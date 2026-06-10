"""大结果磁盘转储截断 — 超阈值时写文件并返回摘要。"""

from __future__ import annotations

import os

import aiofiles

from agent_framework.tools.types import ToolResult

RESULT_DUMP_DIR = ".agent_results"
MAX_RESULT_CHARS = 20_000
PREVIEW_HEAD_CHARS = 250
PREVIEW_TAIL_CHARS = 250


async def truncate_if_needed(
    result: ToolResult, tool_call_id: str, workdir: str
) -> ToolResult:
    """超过阈值时将完整结果写入磁盘，返回摘要 ToolResult。"""
    if len(result.content) <= MAX_RESULT_CHARS:
        return result

    original_length = len(result.content)
    head = result.content[:PREVIEW_HEAD_CHARS]
    tail = result.content[-PREVIEW_TAIL_CHARS:]
    skipped = original_length - PREVIEW_HEAD_CHARS - PREVIEW_TAIL_CHARS
    preview = f"{head}...[省略{skipped}字符]...{tail}"

    dump_dir = os.path.join(workdir, RESULT_DUMP_DIR)
    dump_filename = f"{tool_call_id}.txt"
    dump_path = os.path.join(dump_dir, dump_filename)
    relative_path = f"{RESULT_DUMP_DIR}/{dump_filename}"

    os.makedirs(dump_dir, exist_ok=True)
    async with aiofiles.open(dump_path, "w", encoding="utf-8") as f:
        await f.write(result.content)

    return ToolResult(
        content=(
            f"[工具结果过大({original_length}字符)。"
            f"摘要: {preview} "
            f"完整结果: {relative_path}]"
        ),
        is_error=result.is_error,
        metadata={
            **result.metadata,
            "truncated": True,
            "original_length": original_length,
            "dump_path": dump_path,
        },
    )
