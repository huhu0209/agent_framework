"""每日日志管理器 — append-only 情景记忆存储。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import aiofiles

from agent_framework.memory.types import EventType

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class EpisodicLogManager:
    """管理每日情景记忆日志文件。"""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir

    def _log_path(self, date: str) -> Path:
        """date 格式 YYYY-MM-DD → memory/logs/YYYY/MM/YYYY-MM-DD.md"""
        if not _DATE_RE.match(date):
            raise ValueError(f"日期格式应为 YYYY-MM-DD，得到: {date!r}")
        year, month, _ = date.split("-")
        return self._memory_dir / "logs" / year / month / f"{date}.md"

    async def append(self, timestamp: datetime, event_type: EventType, content: str) -> None:
        """追加一条事件到对应日期的日志文件。"""
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H:%M")
        log_path = self._log_path(date_str)

        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n## [{time_str}] {event_type.value}\n{content}\n"

        async with aiofiles.open(log_path, "a", encoding="utf-8") as f:
            await f.write(entry)

    async def read_log(self, date: str) -> str | None:
        """读取指定日期的日志内容。不存在返回 None。"""
        log_path = self._log_path(date)
        if not log_path.exists():
            return None
        async with aiofiles.open(log_path, "r", encoding="utf-8") as f:
            return await f.read()

    async def write_raw(self, date_str: str, content: str) -> None:
        """直接写入内容到指定日期的日志（供 flush 使用），添加 flush 标记头。"""
        log_path = self._log_path(date_str)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        header = f"\n## [{now.strftime('%H:%M')}] flush\n"
        async with aiofiles.open(log_path, "a", encoding="utf-8") as f:
            await f.write(header + content)

    def list_dates(self) -> list[str]:
        """列出所有有日志的日期（YYYY-MM-DD 格式）。"""
        logs_dir = self._memory_dir / "logs"
        if not logs_dir.exists():
            return []

        dates: list[str] = []
        for year_dir in sorted(logs_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                for log_file in sorted(month_dir.glob("*.md")):
                    dates.append(log_file.stem)

        return dates
