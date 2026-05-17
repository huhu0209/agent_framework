"""最小 ReAct Agent Loop，驱动 LLM 多轮 tool calling。

通过 ToolRouter 执行工具调用，支持内建/MCP/Agent 三类工具来源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

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
    UserMessage,
)
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolCall, ToolUseContext


@dataclass
class LoopEvent:
    """Agent Loop 每一步产生的事件。"""
    type: str  # "step" | "tool_result" | "done" | "max_steps" | "error"
    step: int
    data: dict[str, Any] = field(default_factory=dict)


def _serialize_content(result: CompletionResult) -> list[dict[str, Any]]:
    return [b.model_dump() for b in result.content]


class AgentLoop:
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
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self.max_steps = max_steps
        self.system_prompt = system_prompt

    def _build_config(self, messages: list[Message]) -> CompletionConfig:
        tools = self.router.registry.get_definitions()
        return CompletionConfig(model=self.model, messages=messages, tools=tools)

    def _extract_tool_calls(self, result: CompletionResult) -> list[ToolUseBlock]:
        return [b for b in result.content if isinstance(b, ToolUseBlock)]

    async def _append_assistant_and_tool_results(
        self, messages: list[Message], result: CompletionResult,
    ) -> list[str]:
        """追加 AssistantMessage + 各 ToolMessage，返回每个 tool 的执行结果。"""
        messages.append(AssistantMessage(content=result.content))
        tool_results: list[str] = []
        for tc in self._extract_tool_calls(result):
            call = ToolCall(id=tc.id, name=tc.name, arguments=tc.input)
            tool_result = await self.router.dispatch(call, self.ctx)
            messages.append(ToolMessage(
                tool_call_id=tc.id,
                content=tool_result.content,
            ))
            tool_results.append(tool_result.content)
        return tool_results

    async def run(self, user_message: str) -> AsyncGenerator[LoopEvent, None]:
        """核心异步生成器：执行 ReAct 循环。"""
        messages: list[Message] = [
            SystemMessage(content=self.system_prompt),
            UserMessage(content=[TextBlock(text=user_message)]),
        ]
        for step in range(1, self.max_steps + 1):
            try:
                result = await self.adapter.complete(self._build_config(messages))
            except Exception as exc:
                yield LoopEvent(type="error", step=step, data={"error": str(exc)})
                return

            yield LoopEvent(
                type="step", step=step,
                data={"stop_reason": result.stop_reason.value, "content": _serialize_content(result)},
            )

            if result.stop_reason == StopReason.END_TURN:
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
                return
            if result.stop_reason == StopReason.MAX_TOKENS:
                yield LoopEvent(type="error", step=step, data={"error": "达到 max_tokens 上限"})
                return
            if result.stop_reason == StopReason.STOP_SEQUENCE:
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
                return
            if result.stop_reason == StopReason.TOOL_USE:
                tool_calls = self._extract_tool_calls(result)
                if not tool_calls:
                    yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
                    return
                tool_results = await self._append_assistant_and_tool_results(messages, result)
                yield LoopEvent(
                    type="tool_result", step=step,
                    data={
                        "tool_calls": [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in tool_calls],
                        "tool_results": tool_results,
                    },
                )
                continue

            yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
            return

        yield LoopEvent(type="max_steps", step=self.max_steps, data={})
