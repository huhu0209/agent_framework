"""记忆工具 — 写入情景事件 & 搜索历史记忆。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.types import EventType
from agent_framework.tools.types import ToolResult, ToolUseContext

logger = logging.getLogger(__name__)


async def handle_memory_write(args: dict, ctx: ToolUseContext) -> ToolResult:
    """写入一条情景记忆到当日日志。"""
    memory_dir = ctx.extra.get("memory_dir")
    if memory_dir is None:
        logger.warning("memory_write 调用时缺少 memory_dir 配置")
        return ToolResult(content="记忆系统未配置（缺少 memory_dir）", is_error=True)

    raw_type = args.get("event_type", "")
    content = args.get("content", "")

    if not content.strip():
        return ToolResult(content="content 不能为空", is_error=True)

    try:
        event_type = EventType(raw_type)
    except ValueError:
        valid = ", ".join(t.value for t in EventType)
        return ToolResult(content=f"event_type 无效，可选值: {valid}", is_error=True)

    log_manager = EpisodicLogManager(memory_dir=Path(memory_dir))
    await log_manager.append(datetime.now(), event_type, content)

    return ToolResult(content=f"已记录 [{event_type.value}] {content[:50]}")


async def handle_memory_search(args: dict, ctx: ToolUseContext) -> ToolResult:
    """搜索历史记忆和工作记录（情景 + 语义双层）。"""
    query = args.get("query", "")
    top_k = args.get("top_k", 10)

    memory_store = ctx.extra.get("memory_store")
    if memory_store is not None:
        results = await memory_store.search(query, top_k=top_k)
        if not results:
            return ToolResult(content="未找到相关记忆。")
        parts = []
        for r in results:
            label = "[情景]" if r.source == "episodic" else "[语义]"
            parts.append(f"{label} {r.file}\n{r.content}")
        return ToolResult(content="\n\n".join(parts))

    # fallback: 纯关键词搜索（memory_store 未配置时）
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
