"""记忆搜索 — 从每日日志中搜索历史事件。"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.tools.types import ToolResult, ToolUseContext

logger = logging.getLogger(__name__)


async def handle_memory_search(args: dict, ctx: ToolUseContext) -> ToolResult:
    """搜索历史记忆和工作记录。"""
    query = args.get("query", "")
    top_k = args.get("top_k", 10)

    memory_dir = ctx.extra.get("memory_dir")
    if memory_dir is None:
        logger.warning("memory_search 调用时缺少 memory_dir 配置")
        return ToolResult(content="记忆系统未配置（缺少 memory_dir）", is_error=True)

    log_manager = EpisodicLogManager(memory_dir=Path(memory_dir))
    dates = log_manager.list_dates()

    results: list[str] = []
    for date in reversed(dates):
        content = await log_manager.read_log(date)
        if content is None:
            continue

        blocks = re.split(r"(?=^## )", content, flags=re.MULTILINE)

        for block in blocks:
            if not block.strip():
                continue
            if query.lower() in block.lower():
                results.append(f"[{date}]\n{block.strip()}")
                if len(results) >= top_k:
                    break
        if len(results) >= top_k:
            break

    if not results:
        return ToolResult(content="未找到相关记忆。")

    return ToolResult(content="\n".join(results))
