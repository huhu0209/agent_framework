"""工具路由 — 按来源分叉到正确的执行路径。"""

from __future__ import annotations

from agent_framework.safety.permissions import PermissionDecision, PermissionPipeline
from agent_framework.tools.executor import ToolExecutor
from agent_framework.tools.mcp.config import McpManager
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolCall, ToolResult, ToolUseContext


class ToolRouter:
    """按工具来源路由：builtin / mcp / agent。"""

    def __init__(
        self,
        registry: ToolRegistry,
        mcp_manager: McpManager | None = None,
    ) -> None:
        self.registry = registry
        self._executor = ToolExecutor()
        self._mcp_manager = mcp_manager
        self._permission_pipeline: PermissionPipeline | None = None

    def set_permission_pipeline(self, pipeline: PermissionPipeline) -> None:
        """设置权限管道。"""
        self._permission_pipeline = pipeline

    async def dispatch(self, call: ToolCall, ctx: ToolUseContext) -> ToolResult:
        name = call.name

        # 权限检查
        if self._permission_pipeline is not None:
            decision = self._permission_pipeline.check(name, call.arguments)
            if decision.action == PermissionDecision.DENY:
                return ToolResult(
                    content=f"工具 '{name}' 被拒绝: {decision.reason}",
                    is_error=True,
                )
            if decision.action == PermissionDecision.ASK:
                return ToolResult(
                    content=f"工具 '{name}' 需要用户确认: {decision.reason} (risk: {decision.risk_level.value})",
                    is_error=True,
                )

        if name.startswith("mcp__"):
            return await self._dispatch_mcp(name, call.arguments, ctx)

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

    async def _dispatch_mcp(self, name: str, args: dict, ctx: ToolUseContext) -> ToolResult:
        if self._mcp_manager is None:
            return ToolResult(content="MCP 未配置", is_error=True)

        remainder = name[5:]  # 去掉 "mcp__"
        parts = remainder.split("__", 1)
        if len(parts) != 2:
            return ToolResult(content=f"无效 MCP 工具名: {name}", is_error=True)

        server_name, tool_name = parts
        return await self._mcp_manager.call_tool(server_name, tool_name, args)

    def _dispatch_agent(self, name: str, args: dict, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(
            content=f"Agent 工具 '{name}' 未实现。子 Agent 支持尚未实现。",
            is_error=True,
        )
