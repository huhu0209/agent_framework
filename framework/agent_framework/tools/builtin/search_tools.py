"""搜索工具（当前 mock 实现）。"""

from __future__ import annotations

from agent_framework.tools.types import ToolResult, ToolUseContext


async def web_search(args: dict, ctx: ToolUseContext) -> ToolResult:
    query = args["query"]
    return ToolResult(
        content=(
            f"搜索 '{query}' 的结果：\n"
            f"1. [示例] 关于 '{query}' 的相关信息 - example.com\n"
            f"2. [示例] '{query}' 的详细文档 - docs.example.com\n"
            f"(当前为 mock 搜索，后续接入真实 API)"
        )
    )
