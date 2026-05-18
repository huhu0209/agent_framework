"""计划状态更新工具。"""

from __future__ import annotations

from agent_framework.tools.types import ToolResult, ToolUseContext


async def handle_update_plan_status(args: dict, ctx: ToolUseContext) -> ToolResult:
    state = ctx.extra.get("planning_state")
    if state is None:
        return ToolResult(content="没有活跃计划", is_error=True)

    item_id = args["item_id"]
    new_status = args["status"]

    try:
        state.update_status(item_id, new_status)
    except ValueError as e:
        return ToolResult(content=str(e), is_error=True)

    return ToolResult(content=f"计划项 {item_id} 状态已更新为 {new_status}")
