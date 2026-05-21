"""每日日志管理器 — append-only 情景记忆存储。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agent_framework.memory.types import EventType


class EpisodicLogManager:
    """管理每日情景记忆日志文件。"""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir

    def _log_path(self, date: str) -> Path:
        """date 格式 YYYY-MM-DD → memory/logs/YYYY/MM/YYYY-MM-DD.md"""
        year, month, _ = date.split("-")
        return self._memory_dir / "logs" / year / month / f"{date}.md"

    def append(self, timestamp: datetime, event_type: EventType, content: str) -> None:
        """追加一条事件到对应日期的日志文件。"""
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H:%M")
        log_path = self._log_path(date_str)

        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n## [{time_str}] {event_type.value}\n{content}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def read_log(self, date: str) -> str | None:
        """读取指定日期的日志内容。不存在返回 None。"""
        log_path = self._log_path(date)
        if not log_path.exists():
            return None
        return log_path.read_text(encoding="utf-8")

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
