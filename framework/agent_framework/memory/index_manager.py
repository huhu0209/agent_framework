"""MEMORY.md 索引管理器 — 自动维护语义记忆索引文件。"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)

_MAX_LINES = 200
_MAX_LINE_LENGTH = 150


async def atomic_write(path: Path, content: str) -> None:
    """原子写入：write-to-temp + os.replace，防崩溃截断/并发交错损坏。

    F2: 从 MemoryIndexManager._atomic_write 提取为模块级共享函数，
    供 index_manager 与 semantic_writer._create 复用（消除"只有索引用原子写"的不一致）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".memory_")
    try:
        os.close(fd)
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class MemoryIndexManager:
    """维护 MEMORY.md 索引文件。"""

    def __init__(self, index_path: Path) -> None:
        self._path = index_path

    async def _atomic_write(self, text: str) -> None:
        """原子写入（委托模块级 atomic_write）。"""
        await atomic_write(self._path, text)

    @staticmethod
    def _make_pattern(file_name: str) -> re.Pattern:
        return re.compile(rf"^\- \[.*?\]\({re.escape(file_name)}\) — ")

    async def update(self, file_name: str, name: str, description: str) -> None:
        """新增或更新索引行。>200 行时截断最旧行。"""
        line = self._format_line(file_name, name, description)

        if self._path.exists():
            async with aiofiles.open(self._path, "r", encoding="utf-8") as f:
                content = await f.read()
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
            header: list[str] = []
            body: list[str] = []
            for line in lines:
                if not body and (line.startswith("#") or not line.strip()):
                    header.append(line)
                else:
                    body.append(line)
            max_body = _MAX_LINES - len(header)
            if max_body <= 0:
                lines = header[-_MAX_LINES:]
            else:
                lines = header + body[-max_body:]
            logger.warning("MEMORY.md 索引超 %d 行，执行截断", _MAX_LINES)

        await self._atomic_write("\n".join(lines))

    async def remove(self, file_name: str) -> None:
        """删除索引行。"""
        if not self._path.exists():
            return

        async with aiofiles.open(self._path, "r", encoding="utf-8") as f:
            content = await f.read()
        lines = content.split("\n")

        pattern = self._make_pattern(file_name)
        lines = [l for l in lines if not pattern.match(l)]

        await self._atomic_write("\n".join(lines))

    def _format_line(self, file_name: str, name: str, description: str) -> str:
        line = f"- [{name}]({file_name}) — {description}"
        if len(line) > _MAX_LINE_LENGTH:
            line = line[:_MAX_LINE_LENGTH - 3] + "..."
        return line
