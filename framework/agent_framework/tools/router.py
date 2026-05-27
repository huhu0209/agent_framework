"""工具路由 — 按来源分叉到正确的执行路径。"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from agent_framework.safety.permissions import PermissionDecision, PermissionPipeline
from agent_framework.tools.degrader import ToolDegrader
from agent_framework.tools.executor import ToolExecutor
from agent_framework.tools.mcp.config import McpManager
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolCall, ToolResult, ToolUseContext

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent_framework.hooks.manager import HookManager

# PostToolUse hooks 只能看到截断后的结果，防止 stdin 数据过大
_POST_HOOK_RESULT_LIMIT = 5000


class ToolRouter:
    """按工具来源路由：builtin / mcp / agent。"""

    def __init__(
        self,
        registry: ToolRegistry,
        mcp_manager: McpManager | None = None,
        hook_manager: HookManager | None = None,
        degrader: ToolDegrader | None = None,
    ) -> None:
        self.registry = registry
        self._executor = ToolExecutor()
        self._mcp_manager = mcp_manager
        self._hook_manager = hook_manager
        self._degrader = degrader or ToolDegrader()
        self._permission_pipeline: PermissionPipeline | None = None

    def set_permission_pipeline(self, pipeline: PermissionPipeline) -> None:
        """设置权限管道。"""
        self._permission_pipeline = pipeline

    async def dispatch(self, call: ToolCall, ctx: ToolUseContext) -> ToolResult:
        # lazy import — 避免循环依赖
        from agent_framework.hooks.types import HookContext, HookEvent

        name = call.name

        # 1. 权限检查
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

        # 2. PreToolUse hooks
        active_call = call
        if self._hook_manager is not None:
            pre_ctx = HookContext(
                hook_event_name=HookEvent.PRE_TOOL_USE.value,
                tool_name=name,
                tool_input=call.arguments,
            )
            pre_results = await self._hook_manager.fire(HookEvent.PRE_TOOL_USE, pre_ctx)
            for hr in pre_results:
                if hr.blocked:
                    return ToolResult(
                        content=f"[Hook blocked] {hr.stderr}",
                        is_error=True,
                    )
                if hr.updated_input is not None:
                    active_call = ToolCall(
                        id=call.id,
                        name=call.name,
                        arguments=hr.updated_input,
                    )

        # 3. 执行（含错误恢复和降级）
        try:
            if name.startswith("mcp__"):
                tool_result = await self._dispatch_mcp(name, active_call.arguments, ctx)
            elif name.startswith("agent__"):
                tool_result = self._dispatch_agent(name, active_call.arguments, ctx)
            else:
                tool_result = await self._dispatch_builtin(active_call, ctx)

            # 内置执行器已捕获异常 → 检查 is_error 触发降级
            if tool_result.is_error:
                fallback = self._degrader.get_fallback(name)
                if fallback:
                    logger.warning("工具 '%s' 失败，降级到 '%s': %s", name, fallback, tool_result.content)
                    tool_result = await self._dispatch_builtin(
                        ToolCall(id=active_call.id, name=fallback, arguments=active_call.arguments),
                        ctx,
                    )
        except asyncio.TimeoutError:
            tool_result = ToolResult(
                content=f"工具 '{name}' 执行超时",
                is_error=True,
            )
        except Exception as exc:
            fallback = self._degrader.get_fallback(name)
            if fallback:
                logger.warning("工具 '%s' 失败，降级到 '%s': %s", name, fallback, exc)
                tool_result = await self._dispatch_builtin(
                    ToolCall(id=active_call.id, name=fallback, arguments=active_call.arguments),
                    ctx,
                )
            else:
                tool_result = ToolResult(
                    content=f"工具 '{name}' 执行失败: {exc}",
                    is_error=True,
                )

        # 4. PostToolUse hooks
        if self._hook_manager is not None:
            truncated = tool_result.content[:_POST_HOOK_RESULT_LIMIT]
            post_ctx = HookContext(
                hook_event_name=HookEvent.POST_TOOL_USE.value,
                tool_name=name,
                tool_input=active_call.arguments,
                tool_result=truncated,
            )
            post_results = await self._hook_manager.fire(HookEvent.POST_TOOL_USE, post_ctx)
            for hr in post_results:
                # PostToolUse 已在工具执行后触发，blocked 无法撤回结果，只处理 inject
                if hr.inject_message:
                    tool_result = ToolResult(
                        content=f"{tool_result.content}\n\n[Hook supplement]\n{hr.inject_message}",
                        is_error=tool_result.is_error,
                        metadata=tool_result.metadata,
                    )

        return tool_result

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
