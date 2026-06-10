"""SSE 解析与流式事件处理。

提供：
1. SSE 行解析（通用，可用于 OpenAI/DeepSeek/Anthropic）
2. OpenAI delta 流解析器（将 SSE chunks 转为统一的 StreamEvent）
3. StreamCollector（消费流式事件，收集完整结果）

设计原则：
- 不强求统一各家的流式协议
- 解析器是纯函数/生成器，易于测试
- StreamCollector 提供便捷的消费接口（text_stream / collect）
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from .types import (
    CompletionResult,
    ContentBlock,
    StopReason,
    StreamEvent,
    StreamEventType,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    UsageStats,
)


# ============================================================
# SSE 通用解析
# ============================================================


async def parse_sse_lines(
    lines: AsyncIterator[str],
) -> AsyncIterator[dict]:
    """从 SSE 文本行中提取 JSON 数据。

    SSE 协议：
    - 以 "data: " 开头的行是数据行
    - "data: [DONE]" 表示流结束
    - 空行是事件分隔符
    - 其他行（event:, id:, retry:）暂不处理

    Args:
        lines: 原始 SSE 文本行流

    Yields:
        解析后的 JSON 字典
    """
    async for line in lines:
        if not line.startswith("data: "):
            continue

        payload = line[6:].strip()
        if payload == "[DONE]":
            break

        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


# ============================================================
# OpenAI/DeepSeek 流式解析
# ============================================================


class OpenAIStreamParser:
    """OpenAI ChatCompletions 流式响应解析器。

    处理三类 delta：
    - delta.content → TEXT_DELTA
    - delta.reasoning_content → THINKING_DELTA（DeepSeek 特有）
    - delta.tool_calls[i] → TOOL_USE_START/DELTA/END

    维护 tool_calls 的增量拼接状态。
    """

    def __init__(self) -> None:
        self._tool_calls_buffer: dict[int, dict] = {}

    def parse_chunk(self, chunk: dict) -> list[StreamEvent]:
        """解析一个 SSE chunk 为 StreamEvent 列表。

        一个 chunk 可能产生 0 个或多个事件（如同时有 text 和 tool_call delta）。
        """
        events: list[StreamEvent] = []
        choices = chunk.get("choices", [])

        # 无 choices 的 chunk（如独立 usage chunk）
        if not choices:
            usage = chunk.get("usage")
            if usage:
                events.append(StreamEvent(
                    type=StreamEventType.USAGE,
                    data={"usage": usage},
                    provider_event=chunk,
                ))
            return events

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        # 文本 delta
        content = delta.get("content")
        if content:
            events.append(StreamEvent(
                type=StreamEventType.TEXT_DELTA,
                data={"text": content},
                provider_event=chunk,
            ))

        # reasoning_content delta（DeepSeek）
        reasoning = delta.get("reasoning_content")
        if reasoning:
            events.append(StreamEvent(
                type=StreamEventType.THINKING_DELTA,
                data={"thinking": reasoning},
                provider_event=chunk,
            ))

        # tool_calls delta
        for tc in delta.get("tool_calls", []):
            idx = tc.get("index", 0)

            if idx not in self._tool_calls_buffer:
                self._tool_calls_buffer[idx] = {
                    "id": tc.get("id", ""),
                    "function": {"name": "", "arguments": ""},
                }
                events.append(StreamEvent(
                    type=StreamEventType.TOOL_USE_START,
                    data={"index": idx, "id": tc.get("id", "")},
                    provider_event=chunk,
                ))

            func_delta = tc.get("function", {})
            if func_delta.get("name"):
                self._tool_calls_buffer[idx]["function"]["name"] += func_delta["name"]
            if func_delta.get("arguments"):
                self._tool_calls_buffer[idx]["function"]["arguments"] += func_delta["arguments"]

            events.append(StreamEvent(
                type=StreamEventType.TOOL_USE_DELTA,
                data={
                    "index": idx,
                    "arguments_delta": func_delta.get("arguments", ""),
                },
                provider_event=chunk,
            ))

        # 流结束
        if finish_reason:
            # 输出完整的 tool calls
            for idx, tc in self._tool_calls_buffer.items():
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {"_raw": tc["function"]["arguments"]}
                events.append(StreamEvent(
                    type=StreamEventType.TOOL_USE_END,
                    data={
                        "index": idx,
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": args,
                    },
                    provider_event=chunk,
                ))

            usage = chunk.get("usage")
            if usage:
                events.append(StreamEvent(
                    type=StreamEventType.USAGE,
                    data={"usage": usage},
                    provider_event=chunk,
                ))

            events.append(StreamEvent(type=StreamEventType.DONE))

        return events

    def reset(self) -> None:
        """重置内部状态（新一轮流式请求前调用）。"""
        self._tool_calls_buffer.clear()


# ============================================================
# StreamCollector
# ============================================================


class StreamCollector:
    """流式事件收集器。

    提供三种消费方式：
    1. text_stream() → 只获取文本内容的异步迭代器
    2. thinking_stream() → 只获取思考过程的异步迭代器
    3. collect() → 收集完整 CompletionResult（含 tool calls）

    用法：
        collector = StreamCollector(model="deepseek-v4-pro")
        async for event in provider.stream(config):
            collector.feed(event)
            # 可以同时做其他处理
        result = await collector.collect()
    """

    def __init__(self, *, model: str = "") -> None:
        self._model = model
        self._text_parts: list[str] = []
        self._thinking_parts: list[str] = []
        self._tool_uses: list[ContentBlock] = []
        self._stop_reason: StopReason = StopReason.END_TURN
        self._usage = UsageStats()
        self._done = False
        self._error: str | None = None

    @property
    def is_done(self) -> bool:
        return self._done

    @property
    def error(self) -> str | None:
        return self._error

    def feed(self, event: StreamEvent) -> None:
        """消费一个流式事件，累积到内部状态。"""
        if event.type == StreamEventType.TEXT_DELTA:
            self._text_parts.append(event.data.get("text", ""))

        elif event.type == StreamEventType.THINKING_DELTA:
            self._thinking_parts.append(event.data.get("thinking", ""))

        elif event.type == StreamEventType.TOOL_USE_END:
            self._tool_uses.append(ToolUseBlock(
                id=event.data.get("id", ""),
                name=event.data.get("name", ""),
                input=event.data.get("input", {}),
            ))
            # 有 tool call 时 stop_reason 为 TOOL_USE
            self._stop_reason = StopReason.TOOL_USE

        elif event.type == StreamEventType.USAGE:
            usage_data = event.data.get("usage", {})
            self._usage = UsageStats(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                cache_read_tokens=usage_data.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            )

        elif event.type == StreamEventType.ERROR:
            self._error = event.data.get("error", "Unknown streaming error")

        elif event.type == StreamEventType.DONE:
            self._done = True

    def collect(self) -> CompletionResult:
        """收集所有已 feed 的事件，返回完整 CompletionResult。"""
        content_blocks: list[ContentBlock] = []

        text = "".join(self._text_parts)
        if text:
            content_blocks.append(TextBlock(text=text))

        thinking = "".join(self._thinking_parts)
        if thinking:
            content_blocks.append(ThinkingBlock(thinking=thinking))

        content_blocks.extend(self._tool_uses)

        return CompletionResult(
            id="",
            model=self._model,
            content=content_blocks,
            stop_reason=self._stop_reason,
            usage=self._usage,
        )

    def get_text_so_far(self) -> str:
        """获取到目前为止收集到的文本。"""
        return "".join(self._text_parts)

    def get_thinking_so_far(self) -> str:
        """获取到目前为止收集到的思考过程。"""
        return "".join(self._thinking_parts)
