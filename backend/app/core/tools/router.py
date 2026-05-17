"""工具路由 — 按来源分叉到正确的执行路径。"""

from __future__ import annotations

from app.core.tools.executor import ToolExecutor
from app.core.tools.registry import ToolRegistry
from app.core.tools.types import ToolCall, ToolResult, ToolUseContext


class ToolRouter:
    """按工具来源路由：builtin / mcp / agent。"""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self._executor = ToolExecutor()

    async def dispatch(self, call: ToolCall, ctx: ToolUseContext) -> ToolResult:
        name = call.name

        if name.startswith("mcp__"):
            return self._dispatch_mcp(name, call.arguments, ctx)

        if name.startswith("agent__"):
            return self._dispatch_agent(name, call.arguments, ctx)

        return await self._dispatch_builtin(call, ctx)

    async def _dispatch_builtin(self, call: ToolCall, ctx: ToolUseContext) -> ToolResult:
        spec = self.registry.get(call.name)
        if spec is None:
            return ToolResult(
                content=f"未知工具: {call.name}",
                is_error=True,
            )
        return await self._executor.execute(spec, call.arguments, ctx)

    def _dispatch_mcp(self, name: str, args: dict, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(
            content=f"MCP 工具 '{name}' 未连接。MCP 支持尚未实现。",
            is_error=True,
        )

    def _dispatch_agent(self, name: str, args: dict, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(
            content=f"Agent 工具 '{name}' 未实现。子 Agent 支持尚未实现。",
            is_error=True,
        )
