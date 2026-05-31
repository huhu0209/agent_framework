"""最小 ReAct Agent Loop，驱动 LLM 多轮 tool calling。

通过 ToolRouter 执行工具调用，支持内建/MCP/Agent 三类工具来源。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, TYPE_CHECKING

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm import (
    AssistantMessage,
    CompletionConfig,
    CompletionResult,
    ILLMAdapter,
    Message,
    StopReason,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)
from agent_framework.orchestrator.planner import (
    DriftLevel,
    PlanItem,
    PlanSnapshot,
    PlanningState,
    parse_plan_response,
    strip_plan_tags,
)
from agent_framework.memory.semantic_extractor import SemanticExtractor
from agent_framework.prompts.assembler import PromptAssembler
from agent_framework.prompts.profiles import AgentProfile
from agent_framework.prompts.templates import DRIFT_WARN_TEMPLATE
from agent_framework.tools.context.compactor import CompactConfig, compact, should_compact
from agent_framework.tools.context.token_counter import (
    estimate_tokens,
    estimate_with_usage,
    get_effective_window,
)
from agent_framework.skills.registry import SkillRegistry
from agent_framework.skills.tool import create_load_skill_spec
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolCall, ToolUseContext

if TYPE_CHECKING:
    from agent_framework.hooks.manager import HookManager
    from agent_framework.tasks.runner import TaskRunner
    from agent_framework.teams.manager import TeamManager

@dataclass
class LoopEvent(AgentEvent):
    """Agent Loop 每一步产生的事件。"""

    plan: PlanSnapshot | None = None


def _serialize_content(result: CompletionResult) -> list[dict[str, Any]]:
    return [b.model_dump() for b in result.content]


class AgentLoop(Agent):
    """最小 ReAct 循环，驱动 LLM 多轮 tool calling。"""

    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        max_steps: int = 10,
        system_prompt: str = "你是一个有用的助手。可以使用工具来完成任务。",
        profile: AgentProfile | None = None,
        drift_warn: int = 3,
        drift_abort: int = 8,
        compact_adapter: ILLMAdapter | None = None,
        compact_keep_turns: int = 20,
        compact_trigger_pct: float = 0.75,
        memory_flush_enabled: bool = False,
        semantic_extractor: SemanticExtractor | None = None,
        skill_dirs: list[Path] | None = None,
        hook_manager: HookManager | None = None,
        task_runner: TaskRunner | None = None,
        enable_subagent: bool = False,
        team_manager: TeamManager | None = None,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self.max_steps = max_steps
        self.drift_warn = drift_warn
        self.drift_abort = drift_abort
        self.compact_adapter = compact_adapter or adapter
        self.compact_keep_turns = compact_keep_turns
        self.compact_trigger_pct = compact_trigger_pct
        self._compact_failures = 0
        self._last_usage: UsageStats | None = None
        self._messages_at_last_call = 0
        self._messages: list[Message] = []
        self.profile = profile

        # Skills 集成
        self._skill_registry = SkillRegistry(skill_dirs) if skill_dirs else None
        self._assembler = PromptAssembler(skill_registry=self._skill_registry)
        self._hook_manager = hook_manager
        self._task_runner = task_runner
        self._team_manager = team_manager

        if self._skill_registry is not None:
            spec = create_load_skill_spec()
            self.router.registry.register(spec)
            self.ctx.extra["skill_registry"] = self._skill_registry

        # Integration hook: enable episodic memory flush at end of conversation.
        self._memory_flush_enabled = memory_flush_enabled
        # Integration hook: extract semantic memories from conversation.
        self._semantic_extractor = semantic_extractor

        if enable_subagent:
            from agent_framework.agents.sub_agent import create_run_subagent_spec
            spec = create_run_subagent_spec(adapter, model, self.router, self.ctx)
            self.router.registry.register(spec)

        if self.profile is not None:
            self._system_prompt_text = self._assembler.render(self.profile)
        elif self._skill_registry is not None:
            catalog = self._skill_registry.describe_available()
            self._system_prompt_text = (
                f"{system_prompt}\n\n"
                f"可用 Skills（按需调用 load_skill 加载完整指令）：\n{catalog}"
            )
        else:
            self._system_prompt_text = system_prompt

    def _build_config(self, messages: list[Message]) -> CompletionConfig:
        tools = self.router.registry.get_definitions()
        return CompletionConfig(model=self.model, messages=messages, tools=tools)

    def _extract_tool_calls(self, result: CompletionResult) -> list[ToolUseBlock]:
        return [b for b in result.content if isinstance(b, ToolUseBlock)]

    def _make_plan_snapshot(self, state: PlanningState | None) -> PlanSnapshot | None:
        if state is None:
            return None
        return state.snapshot()

    def _try_parse_plan(
        self, result: CompletionResult, existing_state: PlanningState | None,
    ) -> PlanningState | None:
        if existing_state is not None:
            return existing_state
        text = self._extract_text(result)
        if text is None:
            return existing_state
        items = parse_plan_response(text)
        if items is None:
            return existing_state
        state = PlanningState(items=items, current_focus=None, plan_source="llm_generated")
        self.ctx.extra["planning_state"] = state
        return state

    def _extract_text(self, result: CompletionResult) -> str | None:
        for block in result.content:
            if isinstance(block, TextBlock):
                return block.text
        return None

    def _strip_plan_from_content(self, content: list) -> list:
        cleaned = []
        for block in content:
            if isinstance(block, TextBlock):
                stripped = strip_plan_tags(block.text)
                cleaned.append(TextBlock(text=stripped))
            else:
                cleaned.append(block)
        return cleaned

    def _is_plan_context_message(self, msg: Message) -> bool:
        """Check if a message is a plan context injection."""
        if not isinstance(msg, UserMessage):
            return False
        if not msg.content:
            return False
        first = msg.content[0]
        if not isinstance(first, TextBlock):
            return False
        return first.text.startswith("当前计划进度：") or first.text.startswith("[偏离提醒]")

    async def _maybe_compact(
        self,
        messages: list[Message],
        step: int,
    ) -> list[Message]:
        """每轮调用前检查是否需要压缩。"""
        config = self._build_config(messages)
        window = get_effective_window(self.adapter, config)
        compact_config = CompactConfig(
            keep_turns=self.compact_keep_turns,
            trigger_pct=self.compact_trigger_pct,
        )

        # Token estimation
        if self._last_usage is not None and self._messages_at_last_call > 0:
            new_msgs = messages[self._messages_at_last_call:]
            estimated = estimate_with_usage(new_msgs, self._last_usage)
        else:
            estimated = estimate_tokens(messages)

        if not should_compact(estimated, window, compact_config):
            return messages

        # Circuit breaker: skip after 3 consecutive failures
        if self._compact_failures >= 3:
            return messages

        try:
            result = await compact(
                messages, self.compact_adapter, self.model, compact_config, step,
            )
            self._compact_failures = 0
            return result
        except Exception:
            self._compact_failures += 1
            return messages

    def _inject_plan_context(self, messages: list[Message], state: PlanningState) -> None:
        plan_text = state.format_for_injection()
        drift_text = ""
        drift = state.check_drift(self.drift_warn, self.drift_abort)
        if drift == DriftLevel.WARN:
            drift_text = DRIFT_WARN_TEMPLATE.format(drift_count=state.drift_count, plan_text=plan_text) + "\n\n"
        context = f"{drift_text}{plan_text}"
        plan_msg = UserMessage(content=[TextBlock(text=context)])
        messages.append(plan_msg)

    async def run(
        self,
        user_message: str,
        plan: list[PlanItem] | None = None,
        *,
        resume: bool = False,
    ) -> AsyncGenerator[LoopEvent, None]:
        """核心异步生成器：执行 ReAct 循环，支持 Session Planning。"""
        from agent_framework.tasks.types import RuntimeTaskStatus

        # 0. 初始化消息列表
        if resume and self._messages:
            self._messages.append(
                UserMessage(content=[TextBlock(text=user_message)])
            )
        else:
            self._messages = [
                SystemMessage(content=self._system_prompt_text),
                UserMessage(content=[TextBlock(text=user_message)]),
            ]

        # SessionStart hook
        if self._hook_manager is not None:
            from agent_framework.hooks.types import HookContext, HookEvent

            ss_ctx = HookContext(hook_event_name=HookEvent.SESSION_START.value)
            for result in await self._hook_manager.fire(HookEvent.SESSION_START, ss_ctx):
                if result.inject_message:
                    self._messages.append(UserMessage(content=[
                        TextBlock(text=f"[Hook] {result.inject_message}")
                    ]))

        planning_state: PlanningState | None = None
        # 1. 如果提供了计划，初始化计划状态
        if plan is not None:
            planning_state = PlanningState(
                items=[PlanItem(id=i.id, action=i.action, status=i.status) for i in plan],
                current_focus=None,
                plan_source="caller_injected",
            )
            self.ctx.extra["planning_state"] = planning_state

        plan_checked = False

        for step in range(1, self.max_steps + 1):
            # Drain 后台任务通知
            if self._task_runner is not None:
                notifications = await self._task_runner.drain_notifications()
                for note in notifications:
                    status_text = {
                        RuntimeTaskStatus.COMPLETED: "已完成",
                        RuntimeTaskStatus.ERROR: "失败",
                        RuntimeTaskStatus.TIMEOUT: "超时",
                    }.get(note.status, note.status.value)
                    msg = (
                        f"<task-notification>\n"
                        f"任务 #{note.task_id} {status_text}\n"
                        f"{note.output or note.error}\n"
                        f"</task-notification>"
                    )
                    self._messages.append(UserMessage(content=[TextBlock(text=msg)]))

            # Drain 队友通知
            if self._team_manager is not None:
                while True:
                    try:
                        note = self._team_manager.notifications.get_nowait()
                        self._messages.append(UserMessage(content=[TextBlock(
                            text=f"<team-notification>{note.name} 已关闭</team-notification>"
                        )]))
                    except asyncio.QueueEmpty:
                        break

            if planning_state is not None:
                # Remove previous plan context message (search entire list)
                for i in range(len(self._messages) - 1, -1, -1):
                    if self._is_plan_context_message(self._messages[i]):
                        self._messages.pop(i)
                        break
                self._inject_plan_context(self._messages, planning_state)

            try:
                # Context management
                self._messages = await self._maybe_compact(self._messages, step)

                result = await self.adapter.complete(self._build_config(self._messages))

                # Track usage for hybrid estimation
                self._last_usage = result.usage
                self._messages_at_last_call = len(self._messages)
            except Exception as exc:
                yield LoopEvent(type="error", step=step, data={"error": str(exc)}, plan=self._make_plan_snapshot(planning_state))
                return

            plan_snapshot = self._make_plan_snapshot(planning_state)

            yield LoopEvent(
                type="step", step=step,
                data={"stop_reason": result.stop_reason.value, "content": _serialize_content(result)},
                plan=plan_snapshot,
            )

            if result.stop_reason == StopReason.END_TURN:
                planning_state = self._try_parse_plan(result, planning_state)
                plan_checked = True
                self._messages.append(AssistantMessage(content=result.content))
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=self._make_plan_snapshot(planning_state))
                return

            if result.stop_reason == StopReason.MAX_TOKENS:
                yield LoopEvent(type="error", step=step, data={"error": "达到 max_tokens 上限"}, plan=self._make_plan_snapshot(planning_state))
                return

            if result.stop_reason == StopReason.STOP_SEQUENCE:
                planning_state = self._try_parse_plan(result, planning_state)
                plan_checked = True
                self._messages.append(AssistantMessage(content=result.content))
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=self._make_plan_snapshot(planning_state))
                return

            if result.stop_reason == StopReason.TOOL_USE:
                tool_calls = self._extract_tool_calls(result)
                if not tool_calls:
                    yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=plan_snapshot)
                    return

                cleaned_content = self._strip_plan_from_content(result.content)
                self._messages.append(AssistantMessage(content=cleaned_content))

                tool_results: list[str] = []
                for tc in tool_calls:
                    call = ToolCall(id=tc.id, name=tc.name, arguments=tc.input)
                    tool_result = await self.router.dispatch(call, self.ctx)
                    self._messages.append(ToolMessage(tool_call_id=tc.id, content=tool_result.content))
                    tool_results.append(tool_result.content)

                if planning_state is not None and not plan_checked:
                    planning_state = self._try_parse_plan(result, planning_state)
                    plan_checked = True

                if planning_state is not None:
                    planning_state.drift_count += 1
                    drift = planning_state.check_drift(self.drift_warn, self.drift_abort)
                    if drift == DriftLevel.ABORT:
                        yield LoopEvent(
                            type="error", step=step,
                            data={"error": f"偏离计划：连续 {planning_state.drift_count} 步未推进任何计划项"},
                            plan=self._make_plan_snapshot(planning_state),
                        )
                        return

                yield LoopEvent(
                    type="tool_result", step=step,
                    data={
                        "tool_calls": [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in tool_calls],
                        "tool_results": tool_results,
                    },
                    plan=self._make_plan_snapshot(planning_state),
                )
                continue

            self._messages.append(AssistantMessage(content=result.content))
            yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=plan_snapshot)
            return

        yield LoopEvent(type="max_steps", step=self.max_steps, data={}, plan=self._make_plan_snapshot(planning_state))
