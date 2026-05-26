"""streaming 模块测试 — SSE 解析、OpenAIStreamParser、StreamCollector。"""

from __future__ import annotations

import json

import pytest

from agent_framework.llm.streaming import OpenAIStreamParser, StreamCollector, parse_sse_lines
from agent_framework.llm.types import (
    StopReason,
    StreamEvent,
    StreamEventType,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    UsageStats,
)


# ============================================================
# Helpers
# ============================================================


async def _aiter(items: list[str]) -> list[str]:
    """把 list 包装为 async iterator，供 parse_sse_lines 消费。"""

    for item in items:
        yield item


def _text_delta_chunk(content: str, finish_reason: str | None = None) -> dict:
    """构造一个 OpenAI text delta chunk。"""
    choice: dict = {"delta": {"content": content}}
    if finish_reason:
        choice["finish_reason"] = finish_reason
    return {"choices": [choice]}


def _reasoning_chunk(reasoning: str) -> dict:
    """构造一个 DeepSeek reasoning_content delta chunk。"""
    return {"choices": [{"delta": {"reasoning_content": reasoning}}]}


def _tool_call_start_chunk(index: int, call_id: str, name: str) -> dict:
    """构造 tool_calls 的首个 chunk（含 id 和 function.name）。"""
    return {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {"index": index, "id": call_id, "function": {"name": name, "arguments": ""}}
                    ]
                }
            }
        ]
    }


def _tool_call_delta_chunk(index: int, arguments: str) -> dict:
    """构造 tool_calls 的后续 arguments delta chunk。"""
    return {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {"index": index, "function": {"arguments": arguments}}
                    ]
                }
            }
        ]
    }


def _usage_only_chunk(input_tokens: int, output_tokens: int) -> dict:
    """构造独立的 usage chunk（无 choices）。"""
    return {
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
        }
    }


# ============================================================
# parse_sse_lines
# ============================================================


class TestParseSseLines:
    """SSE 行解析测试。"""

    async def _collect(self, lines: list[str]) -> list[dict]:
        """收集 parse_sse_lines 的所有输出。"""
        result = []
        async for item in parse_sse_lines(_aiter(lines)):
            result.append(item)
        return result

    @pytest.mark.asyncio
    async def test_filters_data_prefix(self) -> None:
        """只处理以 'data: ' 开头的行。"""
        lines = [
            "event: message_start",
            'data: {"foo": 1}',
            ": this is a comment",
        ]
        result = await self._collect(lines)
        assert len(result) == 1
        assert result[0] == {"foo": 1}

    @pytest.mark.asyncio
    async def test_done_stops_iteration(self) -> None:
        """data: [DONE] 终止迭代，后续行不处理。"""
        lines = [
            'data: {"a": 1}',
            "data: [DONE]",
            'data: {"b": 2}',
        ]
        result = await self._collect(lines)
        assert len(result) == 1
        assert result[0] == {"a": 1}

    @pytest.mark.asyncio
    async def test_invalid_json_skipped(self) -> None:
        """无效 JSON 静默跳过，不抛异常。"""
        lines = [
            'data: not json at all',
            'data: {"valid": true}',
            'data: {broken',
        ]
        result = await self._collect(lines)
        assert len(result) == 1
        assert result[0] == {"valid": True}

    @pytest.mark.asyncio
    async def test_empty_lines_ignored(self) -> None:
        """空行和纯空格行被忽略。"""
        lines = [
            "",
            'data: {"ok": 1}',
            "   ",
        ]
        result = await self._collect(lines)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_multiple_valid_data(self) -> None:
        """多个有效 data 行全部产出。"""
        lines = [
            'data: {"i": 1}',
            'data: {"i": 2}',
            'data: {"i": 3}',
        ]
        result = await self._collect(lines)
        assert len(result) == 3
        assert [r["i"] for r in result] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_data_with_trailing_whitespace(self) -> None:
        """data 行尾部空格被 strip。"""
        lines = ['data: {"x": 42}   ']
        result = await self._collect(lines)
        assert len(result) == 1
        assert result[0] == {"x": 42}


# ============================================================
# OpenAIStreamParser
# ============================================================


class TestOpenAIStreamParser:
    """OpenAI 格式 SSE chunk 解析测试。"""

    def test_text_delta(self) -> None:
        """delta.content 映射为 TEXT_DELTA 事件。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk(_text_delta_chunk("hello"))
        assert len(events) == 1
        assert events[0].type == StreamEventType.TEXT_DELTA
        assert events[0].data["text"] == "hello"

    def test_reasoning_delta(self) -> None:
        """delta.reasoning_content 映射为 THINKING_DELTA 事件。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk(_reasoning_chunk("思考中..."))
        assert len(events) == 1
        assert events[0].type == StreamEventType.THINKING_DELTA
        assert events[0].data["thinking"] == "思考中..."

    def test_finish_reason_triggers_done(self) -> None:
        """finish_reason 存在时产出 DONE 事件。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk(_text_delta_chunk("ok", finish_reason="stop"))
        # 最后一个事件应为 DONE
        assert events[-1].type == StreamEventType.DONE

    def test_usage_only_chunk(self) -> None:
        """无 choices 的独立 usage chunk 产出 USAGE 事件。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk(_usage_only_chunk(100, 50))
        assert len(events) == 1
        assert events[0].type == StreamEventType.USAGE
        assert events[0].data["usage"]["prompt_tokens"] == 100

    def test_empty_chunk_returns_no_events(self) -> None:
        """无 choices 且无 usage 的 chunk 不产出事件。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk({"choices": []})
        assert events == []

    def test_no_choices_no_usage_returns_empty(self) -> None:
        """空 dict 无 choices 无 usage → 空列表。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk({})
        assert events == []

    def test_tool_calls_start(self) -> None:
        """首个 tool_call chunk 产出 TOOL_USE_START 事件。"""
        parser = OpenAIStreamParser()
        events = parser.parse_chunk(_tool_call_start_chunk(0, "call_123", "get_weather"))
        types = [e.type for e in events]
        assert StreamEventType.TOOL_USE_START in types
        start_event = events[0]
        assert start_event.type == StreamEventType.TOOL_USE_START
        assert start_event.data["index"] == 0
        assert start_event.data["id"] == "call_123"

    def test_tool_calls_incremental_assembly(self) -> None:
        """多个 tool_call delta 逐步拼接，finish 时产出 TOOL_USE_END 含完整参数。"""
        parser = OpenAIStreamParser()

        # START
        parser.parse_chunk(_tool_call_start_chunk(0, "call_1", "search"))
        # DELTA
        parser.parse_chunk(_tool_call_delta_chunk(0, '{"qu'))
        parser.parse_chunk(_tool_call_delta_chunk(0, 'ery": "test"}'))
        # END — finish_reason 触发
        finish_chunk = {
            "choices": [
                {
                    "delta": {},
                    "finish_reason": "tool_calls",
                }
            ]
        }
        events = parser.parse_chunk(finish_chunk)

        types = [e.type for e in events]
        assert StreamEventType.TOOL_USE_END in types
        end_event = [e for e in events if e.type == StreamEventType.TOOL_USE_END][0]
        assert end_event.data["name"] == "search"
        assert end_event.data["id"] == "call_1"
        assert end_event.data["input"] == {"query": "test"}
        assert StreamEventType.DONE in types

    def test_tool_calls_invalid_json_args_fallback(self) -> None:
        """tool call arguments 无效 JSON 时 fallback 到 {_raw: ...}。"""
        parser = OpenAIStreamParser()
        parser.parse_chunk(_tool_call_start_chunk(0, "call_x", "run"))
        parser.parse_chunk(_tool_call_delta_chunk(0, "not valid json"))
        events = parser.parse_chunk(
            {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        )
        end_event = [e for e in events if e.type == StreamEventType.TOOL_USE_END][0]
        assert end_event.data["input"] == {"_raw": "not valid json"}

    def test_usage_in_finish_chunk(self) -> None:
        """finish_reason chunk 中若含 usage，同时产出 USAGE 事件。"""
        parser = OpenAIStreamParser()
        chunk = {
            "choices": [{"delta": {"content": "done"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10},
        }
        events = parser.parse_chunk(chunk)
        types = [e.type for e in events]
        assert StreamEventType.USAGE in types
        assert StreamEventType.DONE in types

    def test_reset_clears_tool_buffer(self) -> None:
        """reset 清空 tool_calls 缓冲区，第二轮不残留。"""
        parser = OpenAIStreamParser()
        parser.parse_chunk(_tool_call_start_chunk(0, "call_1", "fn"))
        parser.reset()
        # reset 后，再次 start 不应产出残留的 TOOL_USE_END
        events = parser.parse_chunk(
            {"choices": [{"delta": {}, "finish_reason": "stop"}]}
        )
        tool_end_events = [e for e in events if e.type == StreamEventType.TOOL_USE_END]
        assert len(tool_end_events) == 0


# ============================================================
# StreamCollector
# ============================================================


class TestStreamCollector:
    """StreamCollector 事件累积测试。"""

    def test_text_collection(self) -> None:
        """feed 多个 TEXT_DELTA + DONE → collect 返回完整文本。"""
        collector = StreamCollector(model="test-model")
        collector.feed(StreamEvent(type=StreamEventType.TEXT_DELTA, data={"text": "Hel"}))
        collector.feed(StreamEvent(type=StreamEventType.TEXT_DELTA, data={"text": "lo!"}))
        collector.feed(StreamEvent(type=StreamEventType.DONE))

        assert collector.is_done is True
        result = collector.collect()
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextBlock)
        assert result.content[0].text == "Hello!"
        assert result.model == "test-model"

    def test_thinking_collection(self) -> None:
        """feed THINKING_DELTA → ThinkingBlock 出现在结果中。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(type=StreamEventType.THINKING_DELTA, data={"thinking": "step1"}))
        collector.feed(StreamEvent(type=StreamEventType.THINKING_DELTA, data={"thinking": " step2"}))
        collector.feed(StreamEvent(type=StreamEventType.DONE))

        result = collector.collect()
        thinking_blocks = [b for b in result.content if isinstance(b, ThinkingBlock)]
        assert len(thinking_blocks) == 1
        assert thinking_blocks[0].thinking == "step1 step2"

    def test_tool_use_collection(self) -> None:
        """feed TOOL_USE_END → ToolUseBlock 出现在结果中，stop_reason 为 TOOL_USE。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(
            type=StreamEventType.TOOL_USE_END,
            data={"id": "call_1", "name": "search", "input": {"q": "test"}},
        ))
        collector.feed(StreamEvent(type=StreamEventType.DONE))

        result = collector.collect()
        tool_blocks = [b for b in result.content if isinstance(b, ToolUseBlock)]
        assert len(tool_blocks) == 1
        assert tool_blocks[0].name == "search"
        assert tool_blocks[0].input == {"q": "test"}
        assert result.stop_reason == StopReason.TOOL_USE

    def test_error_sets_error_property(self) -> None:
        """feed ERROR 事件设置 error 属性。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(
            type=StreamEventType.ERROR,
            data={"error": "rate limit exceeded"},
        ))
        assert collector.error == "rate limit exceeded"

    def test_error_default_message(self) -> None:
        """ERROR 事件无 error 字段时使用默认消息。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(type=StreamEventType.ERROR, data={}))
        assert collector.error == "Unknown streaming error"

    def test_get_text_so_far_partial(self) -> None:
        """get_text_so_far 在 DONE 之前可获取部分文本。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(type=StreamEventType.TEXT_DELTA, data={"text": "abc"}))
        assert collector.get_text_so_far() == "abc"
        assert collector.is_done is False

        collector.feed(StreamEvent(type=StreamEventType.TEXT_DELTA, data={"text": "def"}))
        assert collector.get_text_so_far() == "abcdef"

    def test_get_thinking_so_far(self) -> None:
        """get_thinking_so_far 在 DONE 之前可获取部分思考内容。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(type=StreamEventType.THINKING_DELTA, data={"thinking": "hmm"}))
        assert collector.get_thinking_so_far() == "hmm"

    def test_usage_collection(self) -> None:
        """USAGE 事件更新 usage 统计。"""
        collector = StreamCollector()
        collector.feed(StreamEvent(
            type=StreamEventType.USAGE,
            data={"usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "prompt_tokens_details": {"cached_tokens": 30},
            }},
        ))
        collector.feed(StreamEvent(type=StreamEventType.DONE))

        result = collector.collect()
        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50
        assert result.usage.cache_read_tokens == 30

    def test_empty_collect_defaults(self) -> None:
        """未 feed 任何事件时 collect 返回合理默认值。"""
        collector = StreamCollector(model="m")
        result = collector.collect()
        assert result.content == []
        assert result.stop_reason == StopReason.END_TURN
        assert result.usage == UsageStats()

    def test_mixed_text_thinking_tool(self) -> None:
        """混合 TEXT_DELTA + THINKING_DELTA + TOOL_USE_END 全部收集。"""
        collector = StreamCollector(model="deepseek-v4")
        collector.feed(StreamEvent(type=StreamEventType.THINKING_DELTA, data={"thinking": "think"}))
        collector.feed(StreamEvent(type=StreamEventType.TEXT_DELTA, data={"text": "answer"}))
        collector.feed(StreamEvent(
            type=StreamEventType.TOOL_USE_END,
            data={"id": "c1", "name": "run", "input": {}},
        ))
        collector.feed(StreamEvent(type=StreamEventType.DONE))

        result = collector.collect()
        assert len(result.content) == 3
        assert isinstance(result.content[0], TextBlock)
        assert isinstance(result.content[1], ThinkingBlock)
        assert isinstance(result.content[2], ToolUseBlock)
