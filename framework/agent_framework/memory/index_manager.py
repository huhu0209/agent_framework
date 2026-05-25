"""MEMORY.md 索引管理器 — 自动维护语义记忆索引文件。"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_LINES = 200
_MAX_LINE_LENGTH = 150


class MemoryIndexManager:
    """维护 MEMORY.md 索引文件。"""

    def __init__(self, index_path: Path) -> None:
        self._path = index_path

    @staticmethod
    def _make_pattern(file_name: str) -> re.Pattern:
        return re.compile(rf"^\- \[.*?\]\({re.escape(file_name)}\) — ")

    def update(self, file_name: str, name: str, description: str) -> None:
        """新增或更新索引行。>200 行时截断最旧行。"""
        line = self._format_line(file_name, name, description)

        if self._path.exists():
            content = self._path.read_text(encoding="utf-8")
        else:
            content = ""

        lines = content.split("\n") if content else []

        # 查找已有条目
        pattern = self._make_pattern(file_name)
        replace_idx = None
        for i, l in enumerate(lines):
            if pattern.match(l):
                replace_idx = i
                break

        if replace_idx is not None:
            lines[replace_idx] = line
        else:
            # 追加，跳过空行
            if lines and lines[-1] == "":
                lines[-1] = line
                lines.append("")
            else:
                lines.append(line)

        # 截断 — preserve header lines (# prefixed), truncate body only
        if len(lines) > _MAX_LINES:
            logger.debug("MEMORY.md 索引超 %d 行，执行截断", _MAX_LINES)
            header: list[str] = []
            body: list[str] = []
            for line in lines:
                if not body and (line.startswith("#") or not line.strip()):
                    header.append(line)
                else:
                    body.append(line)
            if not body:
                lines = lines[-_MAX_LINES:]
            else:
                lines = header + body[-(_MAX_LINES - len(header)):]

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("\n".join(lines), encoding="utf-8")

    def remove(self, file_name: str) -> None:
        """删除索引行。"""
        if not self._path.exists():
            return

        content = self._path.read_text(encoding="utf-8")
        lines = content.split("\n")

        pattern = self._make_pattern(file_name)
        lines = [l for l in lines if not pattern.match(l)]

        self._path.write_text("\n".join(lines), encoding="utf-8")

    def _format_line(self, file_name: str, name: str, description: str) -> str:
        line = f"- [{name}]({file_name}) — {description}"
        if len(line) > _MAX_LINE_LENGTH:
            line = line[:_MAX_LINE_LENGTH - 3] + "..."
        return line
