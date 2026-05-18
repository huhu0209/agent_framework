"""AgentLoop 测试 — 集成 Tool System。"""

import pytest
from unittest.mock import AsyncMock

from agent_framework.agents.agent_loop import AgentLoop, LoopEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    StopReason,
    TextBlock,
    ToolUseBlock,
    UsageStats,
)
from agent_framework.orchestrator.planner import PlanItem
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


def _make_mock_adapter() -> AsyncMock:
    return AsyncMock(spec=ILLMAdapter)


def _text_result(text: str, stop_reason: StopReason = StopReason.END_TURN) -> CompletionResult:
    return CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=stop_reason,
        usage=UsageStats(),
    )


def _tool_use_result(*tool_calls: ToolUseBlock) -> CompletionResult:
    return CompletionResult(
        id="test-id",
        content=list(tool_calls),
        model="mock",
        stop_reason=StopReason.TOOL_USE,
        usage=UsageStats(),
    )


def _make_tool(name: str, id_: str = "tc_1", **input_kwargs) -> ToolUseBlock:
    return ToolUseBlock(id=id_, name=name, input=input_kwargs)


def _make_loop(adapter, **kwargs) -> AgentLoop:
    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    return AgentLoop(adapter, model="mock", router=router, ctx=ctx, **kwargs)


async def _collect_events(loop: AgentLoop, message: str, plan: list[PlanItem] | None = None) -> list[LoopEvent]:
    return [event async for event in loop.run(message, plan=plan)]


@pytest.mark.asyncio
async def test_direct_answer():
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好")

    types = [e.type for e in events]
    assert types == ["step", "done"]
    assert events[0].step == 1
    adapter.complete.assert_called_once()


@pytest.mark.asyncio
async def test_single_tool_call_read_file(tmp_path):
    """用真实的 read_file tool 执行。"""
    (tmp_path / "test.txt").write_text("hello from file")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="test.txt")),
        _text_result("回答"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "hello from file" in tool_events[0].data["tool_results"][0]
    assert adapter.complete.call_count == 2


@pytest.mark.asyncio
async def test_tool_call_nonexistent_tool():
    """调用不存在的工具返回错误。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("nonexistent_tool")),
        _text_result("回答"),
    ]

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "测试")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "未知工具" in tool_events[0].data["tool_results"][0]


@pytest.mark.asyncio
async def test_max_steps_reached():
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _tool_use_result(_make_tool("read_file", path="x.txt"))

    loop = _make_loop(adapter, max_steps=3)
    events = await _collect_events(loop, "一直调用工具")

    last_event = events[-1]
    assert last_event.type == "max_steps"
    assert last_event.step == 3


@pytest.mark.asyncio
async def test_max_tokens_error():
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("截断...", StopReason.MAX_TOKENS)

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "长文本")

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "max_tokens" in error_events[0].data["error"]


@pytest.mark.asyncio
async def test_parallel_tool_calls(tmp_path):
    """一次返回多个 tool call，批量执行。"""
    (tmp_path / "a.txt").write_text("content A")
    (tmp_path / "b.txt").write_text("content B")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(
            _make_tool("read_file", id_="tc_1", path="a.txt"),
            _make_tool("read_file", id_="tc_2", path="b.txt"),
        ),
        _text_result("回答"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读两个文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert len(tool_events[0].data["tool_results"]) == 2


@pytest.mark.asyncio
async def test_adapter_exception():
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = RuntimeError("连接超时")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "触发异常")

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "连接超时" in error_events[0].data["error"]


@pytest.mark.asyncio
async def test_write_then_read(tmp_path):
    """写文件再读回来的端到端测试。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("write_file", path="output.txt", content="written content")),
        _tool_use_result(_make_tool("read_file", path="output.txt")),
        _text_result("回答"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "写文件再读")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 2
    assert "成功写入" in tool_events[0].data["tool_results"][0]
    assert "written content" in tool_events[1].data["tool_results"][0]
    assert adapter.complete.call_count == 3


def _make_plan_items() -> list[PlanItem]:
    return [
        PlanItem(id="1", action="步骤一", status="pending"),
        PlanItem(id="2", action="步骤二", status="pending"),
    ]


@pytest.mark.asyncio
async def test_caller_injected_plan():
    """调用方注入计划，LoopEvent 携带 plan snapshot。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好", plan=_make_plan_items())

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].plan is not None
    assert done_events[0].plan.total_count == 2
    assert done_events[0].plan.plan_source == "caller_injected"


@pytest.mark.asyncio
async def test_llm_generated_plan():
    """LLM 在回复中输出 <plan> 标记，自动解析。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text="<plan>\n1. 第一步\n2. 第二步\n</plan>\n好的，我来执行")],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(),
    )

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "复杂任务")

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].plan is not None
    assert done_events[0].plan.total_count == 2
    assert done_events[0].plan.plan_source == "llm_generated"


@pytest.mark.asyncio
async def test_no_plan_simple_task():
    """简单任务不生成 plan，行为与之前一致。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好")

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].plan is None


@pytest.mark.asyncio
async def test_drift_abort():
    """连续 N 步 TOOL_USE 不推进计划，ABORT 终止循环。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="a.txt")),
        _tool_use_result(_make_tool("read_file", path="b.txt")),
        _tool_use_result(_make_tool("read_file", path="c.txt")),
    ]

    loop = _make_loop(adapter, drift_warn=2, drift_abort=3)
    events = await _collect_events(loop, "复杂任务", plan=_make_plan_items())

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "偏离计划" in error_events[0].data["error"]
