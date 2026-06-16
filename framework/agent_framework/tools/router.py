"""工具路由 — 按来源分叉到正确的执行路径。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from agent_framework.safety.permissions import PermissionDecision, PermissionPipeline
from agent_framework.tools.degrader import ToolDegrader
from agent_framework.tools.executor import ToolExecutor
from agent_framework.tools.validator import ToolValidator
from agent_framework.tools.mcp.config import McpManager
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolCall, ToolResult, ToolUseContext

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent_framework.hooks.manager import HookManager
    from agent_framework.safety.hitl import HITLManager

# PostToolUse hooks 只能看到截断后的结果，防止 stdin 数据过大
_POST_HOOK_RESULT_LIMIT = 5000

# C2: HITL ASK 等待用户确认的超时（秒）。UI 未连接/用户不响应时避免永久挂起 agent 主循环。
_HITL_ASK_TIMEOUT = 300


class ToolRouter:
    """按工具来源路由：builtin / mcp。"""

    def __init__(
        self,
        registry: ToolRegistry,
        mcp_manager: McpManager | None = None,
        hook_manager: HookManager | None = None,
        degrader: ToolDegrader | None = None,
        hitl_manager: HITLManager | None = None,
    ) -> None:
        self.registry = registry
        self._executor = ToolExecutor()
        self._validator = ToolValidator()  # H-C2: MCP 路径参数校验（复用 builtin 同款校验器）
        self._mcp_manager = mcp_manager
        self._hook_manager = hook_manager
        self._degrader = degrader or ToolDegrader()
        self._hitl_manager = hitl_manager
        self._permission_pipeline: PermissionPipeline | None = None

    def set_permission_pipeline(self, pipeline: PermissionPipeline) -> None:
        """设置权限管道，并把内置工具的 annotations 注册进去。

        B3: ToolSpec.annotations 由开发者在工具定义时声明（可信源），
        在此注册到 pipeline，接通原本零调用方的 register_annotations。
        """
        self._permission_pipeline = pipeline
        for name in self.registry.list_tools():
            spec = self.registry.get(name)
            if spec is not None and spec.annotations:
                pipeline.register_annotations(name, spec.annotations)

    def derive(self, registry: ToolRegistry) -> ToolRouter:
        """创建子路由 — 新 registry，继承所有内部基础设施。"""
        sub = ToolRouter(
            registry=registry,
            mcp_manager=self._mcp_manager,
            hook_manager=self._hook_manager,
            degrader=self._degrader,
            hitl_manager=self._hitl_manager,
        )
        if self._permission_pipeline:
            sub.set_permission_pipeline(self._permission_pipeline)
        return sub

    async def dispatch(self, call: ToolCall, ctx: ToolUseContext) -> ToolResult:
        # 1. 权限检查
        perm_result = await self._check_permission(call.name, call.arguments)
        if perm_result is not None:
            return perm_result

        # 2. PreToolUse hooks
        active_call, hook_result = await self._run_pre_hooks(call)
        if hook_result is not None:
            return hook_result

        # 3. 执行
        tool_result = await self._execute_tool(call.name, active_call, ctx)

        # 4. PostToolUse hooks
        tool_result = await self._run_post_hooks(call.name, active_call.arguments, tool_result)
        return tool_result

    async def _check_permission(self, name: str, args: dict) -> ToolResult | None:
        """权限检查：DENY 直接返回错误，ASK 走 HITL 或返回错误。"""
        if self._permission_pipeline is None:
            return None

        decision = self._permission_pipeline.check(name, args)
        if decision.action == PermissionDecision.DENY:
            return ToolResult(
                content=f"工具 '{name}' 被拒绝: {decision.reason}",
                is_error=True,
            )
        if decision.action == PermissionDecision.ASK:
            return await self._handle_ask(name, args, decision)
        return None

    async def _handle_ask(self, name: str, args: dict, decision: "PermissionResult") -> ToolResult | None:
        """处理 ASK 决定：通过 HITLManager 等待用户确认，或返回错误。"""
        from agent_framework.safety.hitl import PermissionOption, PermissionRequest

        if self._hitl_manager is not None:
            request = PermissionRequest(
                request_id=str(uuid.uuid4()),
                tool_name=name,
                tool_input=args,
                reason=decision.reason,
                risk_level=decision.risk_level,
                options=[
                    PermissionOption(action="approve", label="允许"),
                    PermissionOption(action="approve_once", label="仅本次允许"),
                    PermissionOption(action="approve_session", label="本次会话允许"),
                    PermissionOption(action="deny", label="拒绝"),
                ],
            )
            future = self._hitl_manager.create_pending(request)
            try:
                response = await asyncio.wait_for(future, timeout=_HITL_ASK_TIMEOUT)
            except asyncio.TimeoutError:
                # C2: 超时清理 pending（防内存泄漏），返回错误而非永久挂起
                self._hitl_manager._pending.pop(request.request_id, None)
                return ToolResult(
                    content=f"工具 '{name}' 等待确认超时",
                    is_error=True,
                )
            if response.action == "deny":
                return ToolResult(
                    content=f"工具 '{name}' 被用户拒绝",
                    is_error=True,
                )
            return None

        return ToolResult(
            content=f"工具 '{name}' 需要用户确认: {decision.reason} (risk: {decision.risk_level.value})",
            is_error=True,
        )

    async def _run_pre_hooks(self, call: ToolCall) -> tuple[ToolCall, ToolResult | None]:
        """PreToolUse hooks：返回 (可能修改的 call, 阻断结果或 None)。"""
        from agent_framework.hooks.types import HookContext, HookEvent

        if self._hook_manager is None:
            return call, None

        pre_ctx = HookContext(
            hook_event_name=HookEvent.PRE_TOOL_USE.value,
            tool_name=call.name,
            tool_input=call.arguments,
        )
        pre_results = await self._hook_manager.fire(HookEvent.PRE_TOOL_USE, pre_ctx)
        active_call = call
        for hr in pre_results:
            if hr.blocked:
                return call, ToolResult(
                    content=f"[Hook blocked] {hr.stderr}",
                    is_error=True,
                )
            if hr.updated_input is not None:
                active_call = ToolCall(
                    id=call.id,
                    name=call.name,
                    arguments=hr.updated_input,
                )
        return active_call, None

    async def _execute_tool(self, name: str, call: ToolCall, ctx: ToolUseContext) -> ToolResult:
        """执行工具（mcp / builtin），含错误恢复和降级。"""
        try:
            if name.startswith("mcp__"):
                tool_result = await self._dispatch_mcp(name, call.arguments, ctx)
            else:
                tool_result = await self._dispatch_builtin(call, ctx)

            if tool_result.is_error:
                fallback = self._degrader.get_fallback(name)
                if fallback:
                    logger.warning("工具 '%s' 失败，降级到 '%s': %s", name, fallback, tool_result.content)
                    tool_result = await self._dispatch_builtin(
                        ToolCall(id=call.id, name=fallback, arguments=call.arguments),
                        ctx,
                    )
            return tool_result
        except asyncio.TimeoutError:
            return ToolResult(content=f"工具 '{name}' 执行超时", is_error=True)
        except Exception as exc:
            fallback = self._degrader.get_fallback(name)
            if fallback:
                logger.warning("工具 '%s' 失败，降级到 '%s': %s", name, fallback, exc)
                return await self._dispatch_builtin(
                    ToolCall(id=call.id, name=fallback, arguments=call.arguments),
                    ctx,
                )
            return ToolResult(content=f"工具 '{name}' 执行失败: {exc}", is_error=True)

    async def _run_post_hooks(self, name: str, args: dict, tool_result: ToolResult) -> ToolResult:
        """PostToolUse hooks：处理 inject 补充信息。"""
        from agent_framework.hooks.types import HookContext, HookEvent

        if self._hook_manager is None:
            return tool_result

        truncated = tool_result.content[:_POST_HOOK_RESULT_LIMIT]
        post_ctx = HookContext(
            hook_event_name=HookEvent.POST_TOOL_USE.value,
            tool_name=name,
            tool_input=args,
            tool_result=truncated,
        )
        post_results = await self._hook_manager.fire(HookEvent.POST_TOOL_USE, post_ctx)
        for hr in post_results:
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

        # H-C2: 远程 inputSchema 不可信，调用前校验（与 builtin 路径一致的 ToolValidator）
        spec = self.registry.get(name)
        if spec is not None:
            validation_error = self._validator.validate(spec, args)
            if validation_error is not None:
                return validation_error

        return await self._mcp_manager.call_tool(server_name, tool_name, args)
