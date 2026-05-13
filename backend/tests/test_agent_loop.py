"""AgentLoop 测试。"""

import pytest
from unittest.mock import AsyncMock

from app.core.agents.agent_loop import AgentLoop, LoopEvent
from app.core.llm.base import ILLMAdapter
from app.core.llm.types import (
    CompletionResult,
    StopReason,
    TextBlock,
    ToolUseBlock,
    UsageStats,
)


def _make_mock_adapter() -> AsyncMock:
    """创建 AsyncMock(spec=ILLMAdapter)。"""
    return AsyncMock(spec=ILLMAdapter)


def _text_result(text: str, stop_reason: StopReason = StopReason.END_TURN) -> CompletionResult:
    """构造纯文本 CompletionResult。"""
    return CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=stop_reason,
        usage=UsageStats(),
    )


def _tool_use_result(*tool_calls: ToolUseBlock) -> CompletionResult:
    """构造含 ToolUseBlock 的 CompletionResult。"""
    return CompletionResult(
        id="test-id",
        content=list(tool_calls),
        model="mock",
        stop_reason=StopReason.TOOL_USE,
        usage=UsageStats(),
    )


def _make_tool(name: str, id_: str = "tc_1", **input_kwargs) -> ToolUseBlock:
    """构造 ToolUseBlock 的快捷方法。"""
    return ToolUseBlock(id=id_, name=name, input=input_kwargs)


async def _collect_events(loop: AgentLoop, message: str) -> list[LoopEvent]:
    """收集 AgentLoop.run 的所有事件。"""
    return [event async for event in loop.run(message)]


# ---- 测试 ----


@pytest.mark.asyncio
async def test_direct_answer():
    """模型直接回答不调 tool，一步退出。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答", StopReason.END_TURN)

    loop = AgentLoop(adapter, model="mock")
    events = await _collect_events(loop, "你好")

    types = [e.type for e in events]
    assert types == ["step", "done"]
    assert events[0].step == 1
    assert events[0].data["stop_reason"] == "end_turn"
    assert events[1].data["content"][0]["text"] == "回答"
    adapter.complete.assert_called_once()


@pytest.mark.asyncio
async def test_single_tool_call():
    """模型调一次 tool 后回答。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("get_time")),
        _text_result("回答"),
    ]

    loop = AgentLoop(adapter, model="mock")
    events = await _collect_events(loop, "现在几点了？")

    types = [e.type for e in events]
    assert types == ["step", "tool_result", "step", "done"]

    # tool_result 事件有 tool_calls 和 tool_results
    tool_result_event = events[1]
    assert tool_result_event.type == "tool_result"
    assert len(tool_result_event.data["tool_calls"]) == 1
    assert tool_result_event.data["tool_calls"][0]["name"] == "get_time"
    assert len(tool_result_event.data["tool_results"]) == 1

    assert adapter.complete.call_count == 2


@pytest.mark.asyncio
async def test_multiple_tool_calls():
    """模型连续调 tool。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("get_time", id_="tc_1")),
        _tool_use_result(_make_tool("calculate", id_="tc_2", expression="2+3")),
        _text_result("回答"),
    ]

    loop = AgentLoop(adapter, model="mock")
    events = await _collect_events(loop, "现在几点，2+3等于几？")

    tool_result_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_result_events) == 2

    assert tool_result_events[0].data["tool_calls"][0]["name"] == "get_time"
    assert tool_result_events[1].data["tool_calls"][0]["name"] == "calculate"

    assert adapter.complete.call_count == 3


@pytest.mark.asyncio
async def test_max_steps_reached():
    """达到 max_steps 时终止。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _tool_use_result(_make_tool("get_time"))

    loop = AgentLoop(adapter, model="mock", max_steps=3)
    events = await _collect_events(loop, "一直调用工具")

    last_event = events[-1]
    assert last_event.type == "max_steps"
    assert last_event.step == 3


@pytest.mark.asyncio
async def test_max_tokens_error():
    """MAX_TOKENS 终止时产生 error 事件。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("截断...", StopReason.MAX_TOKENS)

    loop = AgentLoop(adapter, model="mock")
    events = await _collect_events(loop, "长文本")

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "max_tokens" in error_events[0].data["error"]


@pytest.mark.asyncio
async def test_parallel_tool_calls():
    """一次返回多个 tool call，批量执行。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(
            _make_tool("get_time", id_="tc_1"),
            _make_tool("calculate", id_="tc_2", expression="10*2"),
        ),
        _text_result("回答"),
    ]

    loop = AgentLoop(adapter, model="mock")
    events = await _collect_events(loop, "几点了？10*2=?")

    tool_result_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_result_events) == 1

    tr = tool_result_events[0]
    assert len(tr.data["tool_calls"]) == 2
    assert tr.data["tool_calls"][1]["name"] == "calculate"
    assert "20" in tr.data["tool_results"]


@pytest.mark.asyncio
async def test_adapter_exception():
    """Adapter 抛异常时产生 error 事件。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = RuntimeError("连接超时")

    loop = AgentLoop(adapter, model="mock")
    events = await _collect_events(loop, "触发异常")

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "连接超时" in error_events[0].data["error"]
