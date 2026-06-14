"""最小 ReAct Agent Loop，驱动 LLM 多轮 tool calling。

通过 ToolRouter 执行工具调用，支持内建/MCP/Agent 三类工具来源。
"""

from __future__ import annotations

import asyncio
import logging

from dataclasses import dataclass
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
    strip_plan_tags,
)
from agent_framework.orchestrator.planning_session import PlanningSession
from agent_framework.memory.flush import FlushExtractor
from agent_framework.memory.semantic_extractor import SemanticExtractor
from agent_framework.config.loader import ConfigLoader
from agent_framework.prompts.assembler import PromptAssembler
from agent_framework.prompts.profiles import AgentProfile
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

logger = logging.getLogger(__name__)


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
        config_loader: ConfigLoader | None = None,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self.max_steps = max_steps
        self._planning = PlanningSession(allow_replan=True, drift_warn=drift_warn, drift_abort=drift_abort)
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
        self._config_loader = config_loader

        if self._skill_registry is not None:
            spec = create_load_skill_spec()
            self.router.registry.register(spec)
            self.ctx.extra["skill_registry"] = self._skill_registry

        # Integration hook: flush episodic memory before context compaction.
        self._flush_extractor = (
            FlushExtractor(adapter, model) if memory_flush_enabled else None
        )
        # Integration hook: extract semantic memories from conversation.
        self._semantic_extractor = semantic_extractor

        if enable_subagent:
            from agent_framework.agents.sub_agent import create_run_subagent_spec
            spec = create_run_subagent_spec(adapter, model, self.router, self.ctx)
            self.router.registry.register(spec)

        if self.profile is not None:
            self._system_prompt_text = self._assembler.render(
                self._config_loader or ConfigLoader(), self.profile
            )
        elif self._skill_registry is not None:
            catalog = self._skill_registry.describe_available()
            self._system_prompt_text = (
                f"{system_prompt}\n\n"
                f"可用 Skills（按需调用 load_skill 加载完整指令）：\n{catalog}"
            )
        else:
            self._system_prompt_text = system_prompt

        # 注入记忆索引到 system prompt
        memory_dir = self.ctx.extra.get("memory_dir")
        if memory_dir:
            memory_index_path = Path(memory_dir) / "MEMORY.md"
            if memory_index_path.exists():
                index_content = memory_index_path.read_text(encoding="utf-8").strip()
                if index_content:
                    self._system_prompt_text += (
                        f"\n\n# 记忆系统\n"
                        f"## 语义记忆索引\n{index_content}\n\n"
                        f"## 情景记忆\n"
                        f"历史决策、偏好、错误记录存储在每日日志中。"
                        f"使用 memory_search(\"关键词\") 搜索相关历史。"
                    )

            from agent_framework.memory.store import MemoryStore
            self.ctx.extra["memory_store"] = MemoryStore(
                adapter=adapter, model=model, memory_dir=Path(memory_dir),
            )

        # 追加计划生成指令（仅无 profile 时）
        if self.profile is None:
            self._system_prompt_text += "\n\n" + PlanningSession.plan_instruction_prompt()

    @property
    def system_prompt_text(self) -> str:
        """The assembled system prompt text (read-only)."""
        return self._system_prompt_text

    def load_messages(self, messages: list[Message]) -> None:
        """注入历史消息（用于 resume）。前插 SystemMessage 以确保 system prompt 存在。"""
        self._messages = [
            SystemMessage(content=self._system_prompt_text),
            *messages,
        ]

    def _build_config(self, messages: list[Message]) -> CompletionConfig:
        tools = self.router.registry.get_definitions()
        return CompletionConfig(model=self.model, messages=messages, tools=tools)

    def _extract_tool_calls(self, result: CompletionResult) -> list[ToolUseBlock]:
        return [b for b in result.content if isinstance(b, ToolUseBlock)]


    def _extract_text(self, result: CompletionResult) -> str | None:
        for block in result.content:
            if isinstance(block, TextBlock):
                return block.text
        return None

    def _serialize_for_flush(self, messages: list[Message]) -> str:
        """将消息列表序列化为文本字符串，供 flush prompt 使用。"""
        parts: list[str] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role, text = "system", msg.content
            elif isinstance(msg, UserMessage):
                role = "user"
                text = " ".join(b.text for b in msg.content if isinstance(b, TextBlock))
            elif isinstance(msg, AssistantMessage):
                role = "assistant"
                text = " ".join(b.text for b in msg.content if isinstance(b, TextBlock))
            elif isinstance(msg, ToolMessage):
                role, text = "tool", msg.content
            else:
                continue
            if text and text.strip():
                parts.append(f"[{role}] {text.strip()}")
        return "\n\n".join(parts)

    def _strip_plan_from_content(self, content: list) -> list:
        cleaned = []
        for block in content:
            if isinstance(block, TextBlock):
                stripped = strip_plan_tags(block.text)
                cleaned.append(TextBlock(text=stripped))
            else:
                cleaned.append(block)
        return cleaned

    async def _maybe_compact(
        self,
        messages: list[Message],
        step: int,
    ) -> list[Message]:
        """每轮调用前检查是否需要压缩。"""
        from datetime import datetime as dt

        from agent_framework.memory.log_manager import EpisodicLogManager

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

        # Prepare flush (best-effort, parallel with compact)
        flush_coro = None
        _conv_text: str | None = None
        if self._flush_extractor is not None:
            memory_dir = self.ctx.extra.get("memory_dir")
            if memory_dir:
                _conv_text = self._serialize_for_flush(messages)
                log_mgr = EpisodicLogManager(Path(memory_dir))
                existing = await log_mgr.read_log(dt.now().strftime("%Y-%m-%d"))
                flush_coro = self._flush_extractor.flush(
                    _conv_text, dt.now(), log_mgr, existing_log=existing,
                )

        # Circuit breaker: skip after 3 consecutive failures
        if self._compact_failures >= 3:
            return messages

        try:
            if flush_coro is not None:
                _, result = await asyncio.gather(
                    flush_coro,
                    compact(messages, self.compact_adapter, self.model, compact_config, step),
                    return_exceptions=True,
                )
                if isinstance(result, Exception):
                    raise result
            else:
                result = await compact(
                    messages, self.compact_adapter, self.model, compact_config, step,
                )
            self._compact_failures = 0

            # Cascade: extract semantic memories before context is lost
            if self._semantic_extractor is not None:
                memory_dir = self.ctx.extra.get("memory_dir")
                if memory_dir:
                    if _conv_text is None:
                        _conv_text = self._serialize_for_flush(messages)
                    try:
                        drafts = await self._semantic_extractor.extract_from_messages(_conv_text)
                        if drafts:
                            from agent_framework.memory.semantic_writer import SemanticWriter
                            await SemanticWriter(Path(memory_dir)).write_batch(drafts)
                    except Exception:
                        logger.debug("语义记忆提取失败（best-effort）", exc_info=True)

            return result
        except Exception:
            self._compact_failures += 1
            return messages

    # ---- Extracted helpers for run() ----

    def _init_messages(self, user_message: str, resume: bool) -> list[Message]:
        """Initialize or resume the message list."""
        if resume and self._messages:
            messages = list(self._messages)
            messages.append(UserMessage(content=[TextBlock(text=user_message)]))
            return messages
        return [
            SystemMessage(content=self._system_prompt_text),
            UserMessage(content=[TextBlock(text=user_message)]),
        ]

    async def _fire_session_start_hook(self) -> None:
        """Fire SessionStart hook and append inject messages."""
        if self._hook_manager is None:
            return
        from agent_framework.hooks.types import HookContext, HookEvent

        ss_ctx = HookContext(hook_event_name=HookEvent.SESSION_START.value)
        for result in await self._hook_manager.fire(HookEvent.SESSION_START, ss_ctx):
            if result.inject_message:
                self._messages.append(UserMessage(content=[
                    TextBlock(text=f"[Hook] {result.inject_message}")
                ]))

    async def _drain_notifications(self) -> None:
        """Drain task_runner and team_manager notifications into self._messages."""
        from agent_framework.tasks.types import RuntimeTaskStatus

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

        if self._team_manager is not None:
            while True:
                try:
                    note = self._team_manager.notifications.get_nowait()
                    self._messages.append(UserMessage(content=[TextBlock(
                        text=f"<team-notification>{note.name} 已关闭</team-notification>"
                    )]))
                except asyncio.QueueEmpty:
                    break

    def _inject_plan_context(self) -> None:
        """Remove old plan context and inject fresh plan context."""
        if not self._planning.has_plan:
            return
        for i in range(len(self._messages) - 1, -1, -1):
            msg = self._messages[i]
            if isinstance(msg, UserMessage) and msg.content:
                first = msg.content[0]
                if isinstance(first, TextBlock) and self._planning.is_plan_context_text(first.text):
                    self._messages.pop(i)
                    break
        drift_text, plan_text = self._planning.format_context_message()
        if drift_text or plan_text:
            self._messages.append(UserMessage(content=[TextBlock(text=f"{drift_text}{plan_text}")]))

    async def _handle_tool_calls(
        self,
        result: CompletionResult,
        step: int,
        plan_checked: bool,
    ) -> tuple[list[LoopEvent], bool]:
        """Dispatch tool calls, update plan state, check drift.

        Returns (events_to_yield, updated_plan_checked).
        """
        tool_calls = self._extract_tool_calls(result)
        if not tool_calls:
            return (
                [LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=self._planning.snapshot())],
                plan_checked,
            )

        cleaned_content = self._strip_plan_from_content(result.content)
        self._messages.append(AssistantMessage(content=cleaned_content))

        tool_results: list[str] = []
        for tc in tool_calls:
            call = ToolCall(id=tc.id, name=tc.name, arguments=tc.input)
            tool_result = await self.router.dispatch(call, self.ctx)
            self._messages.append(ToolMessage(tool_call_id=tc.id, content=tool_result.content))
            tool_results.append(tool_result.content)

        if self._planning.has_plan and not plan_checked:
            text = self._extract_text(result)
            if text and self._planning.try_parse_from_response(text):
                self.ctx.extra["planning_session"] = self._planning
            plan_checked = True

        if self._planning.has_plan:
            drift = self._planning.increment_drift()
            if drift == DriftLevel.ABORT:
                return (
                    [LoopEvent(
                        type="error", step=step,
                        data={"error": f"偏离计划：连续 {self._planning.drift_count} 步未推进任何计划项"},
                        plan=self._planning.snapshot(),
                    )],
                    plan_checked,
                )

        return (
            [LoopEvent(
                type="tool_result", step=step,
                data={
                    "tool_calls": [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in tool_calls],
                    "tool_results": tool_results,
                },
                plan=self._planning.snapshot(),
            )],
            plan_checked,
        )

    async def run(
        self,
        user_message: str,
        plan: list[PlanItem] | None = None,
        *,
        resume: bool = False,
    ) -> AsyncGenerator[LoopEvent, None]:
        """核心异步生成器：执行 ReAct 循环，支持 Session Planning。"""
        # 0. 初始化消息列表
        self._messages = self._init_messages(user_message, resume)

        # SessionStart hook
        await self._fire_session_start_hook()

        # 1. 如果提供了计划，初始化计划状态
        if plan is not None:
            self._planning.create_from_items(plan, "caller_injected")
            self.ctx.extra["planning_session"] = self._planning

        plan_checked = False

        for step in range(1, self.max_steps + 1):
            await self._drain_notifications()
            self._inject_plan_context()

            try:
                self._messages = await self._maybe_compact(self._messages, step)
                result = await self.adapter.complete(self._build_config(self._messages))
                self._last_usage = result.usage
                self._messages_at_last_call = len(self._messages)
            except Exception as exc:
                yield LoopEvent(type="error", step=step, data={"error": str(exc)}, plan=self._planning.snapshot())
                return

            plan_snapshot = self._planning.snapshot()

            yield LoopEvent(
                type="step", step=step,
                data={"stop_reason": result.stop_reason.value, "content": _serialize_content(result)},
                plan=plan_snapshot,
            )

            # 根据 stop_reason 分流 — 这是核心决策
            if result.stop_reason == StopReason.END_TURN:
                text = self._extract_text(result)
                if text and self._planning.try_parse_from_response(text):
                    self.ctx.extra["planning_session"] = self._planning
                plan_checked = True
                self._messages.append(AssistantMessage(content=result.content))
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=self._planning.snapshot())
                return

            if result.stop_reason == StopReason.MAX_TOKENS:
                yield LoopEvent(type="error", step=step, data={"error": "达到 max_tokens 上限"}, plan=self._planning.snapshot())
                return

            if result.stop_reason == StopReason.STOP_SEQUENCE:
                text = self._extract_text(result)
                if text and self._planning.try_parse_from_response(text):
                    self.ctx.extra["planning_session"] = self._planning
                plan_checked = True
                self._messages.append(AssistantMessage(content=result.content))
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=self._planning.snapshot())
                return

            if result.stop_reason == StopReason.TOOL_USE:
                events, plan_checked = await self._handle_tool_calls(result, step, plan_checked)
                for event in events:
                    yield event
                # If drift abort occurred, the event list contains an error — stop the loop
                if events and events[-1].type == "error":
                    return
                continue

            self._messages.append(AssistantMessage(content=result.content))
            yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)}, plan=plan_snapshot)
            return

        yield LoopEvent(type="max_steps", step=self.max_steps, data={}, plan=self._planning.snapshot())
