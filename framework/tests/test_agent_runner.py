"""AgentRunner 单元测试 — EVNT-05/06/07 + config/system_prompt/source。"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent_framework.agents.agent_loop import AgentLoop, LoopEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import ProviderInfo
from agent_framework.prompts.profiles import AgentProfile
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext
from agent_framework.viz.agent_runner import AgentRunner
from agent_framework.viz.event_bus import EventBus


def _make_loop(profile: "AgentProfile | None" = None) -> AgentLoop:
    """构造最小 AgentLoop；传入 profile 时启用 profile 模式。"""
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    return AgentLoop(
        adapter=adapter,
        model="mock-model",
        router=ToolRouter(create_builtin_registry()),
        ctx=ToolUseContext(),
        profile=profile,
    )


def _make_runner(bus: EventBus | None = None) -> AgentRunner:
    return AgentRunner(_make_loop(), bus or EventBus(), "test-session")


async def _collect_events(
    runner: AgentRunner,
    *events: LoopEvent,
) -> tuple[list[LoopEvent], list[dict[str, Any]]]:
    """运行 wrap() 并收集透传的 LoopEvent + VizEvent。"""

    async def gen() -> Any:
        for e in events:
            yield e

    bus_events: list[dict[str, Any]] = []
    bus = runner._bus
    q = await bus.subscribe()

    yielded: list[LoopEvent] = []
    async for event in runner.wrap(gen()):
        yielded.append(event)

    while not q.empty():
        bus_events.append(q.get_nowait())

    return yielded, bus_events


def _find_by_type(events: list[dict], vtype: str) -> list[dict]:
    return [e for e in events if e["type"] == vtype]


# --- 启动事件：config / system_prompt / idle ---

async def test_publishes_config_on_start() -> None:
    _, viz_events = await _collect_events(_make_runner())
    configs = _find_by_type(viz_events, "config")
    assert len(configs) == 1
    payload = configs[0]["payload"]
    assert payload["model"] == "mock-model"
    assert payload["max_steps"] == 10
    assert "read_file" in payload["tools"]
    assert payload["profile"] is None  # profile=None


async def test_publishes_system_prompt_on_start() -> None:
    _, viz_events = await _collect_events(_make_runner())
    prompts = _find_by_type(viz_events, "system_prompt")
    assert len(prompts) == 1
    assert isinstance(prompts[0]["payload"]["text"], str)
    assert prompts[0]["payload"]["text"]  # 非空
    assert prompts[0]["payload"]["blocks"] == []  # profile=None → 空 blocks


async def test_publishes_idle_before_loop() -> None:
    _, viz_events = await _collect_events(_make_runner())
    types = [e["type"] for e in viz_events]
    assert "idle" in types
    # config/system_prompt 在 idle 之前发出
    assert types.index("config") < types.index("idle")
    assert types.index("system_prompt") < types.index("idle")


async def test_all_events_carry_session_id() -> None:
    _, viz_events = await _collect_events(_make_runner())
    assert all(e["session_id"] == "test-session" for e in viz_events)


# --- 工具调用映射 + source ---

async def test_maps_tool_result_with_builtin_source() -> None:
    runner = _make_runner()
    event = LoopEvent(type="tool_result", step=1, data={
        "tool_calls": [{"id": "tc_1", "name": "read_file", "input": {"path": "f.txt"}}],
        "tool_results": ["content"],
    })
    _, viz_events = await _collect_events(runner, event)
    calls = _find_by_type(viz_events, "tool_call")
    assert calls[0]["payload"]["source"] == "builtin"


async def test_maps_tool_result_with_mcp_source() -> None:
    runner = _make_runner()
    event = LoopEvent(type="tool_result", step=1, data={
        "tool_calls": [{"id": "tc_1", "name": "mcp__server__tool", "input": {}}],
        "tool_results": ["ok"],
    })
    _, viz_events = await _collect_events(runner, event)
    calls = _find_by_type(viz_events, "tool_call")
    results = _find_by_type(viz_events, "tool_result")
    assert calls[0]["payload"]["source"] == "mcp"
    assert results[0]["payload"]["source"] == "mcp"


async def test_maps_tool_result_with_agent_source() -> None:
    runner = _make_runner()
    event = LoopEvent(type="tool_result", step=1, data={
        "tool_calls": [{"id": "tc_1", "name": "run_subagent", "input": {}}],
        "tool_results": ["ok"],
    })
    _, viz_events = await _collect_events(runner, event)
    calls = _find_by_type(viz_events, "tool_call")
    assert calls[0]["payload"]["source"] == "agent"


async def test_maps_multiple_tools_with_mixed_sources() -> None:
    """回归保护：多工具循环 + 混合 source 推断。"""
    runner = _make_runner()
    event = LoopEvent(type="tool_result", step=1, data={
        "tool_calls": [
            {"id": "tc_1", "name": "read_file", "input": {"path": "a"}},
            {"id": "tc_2", "name": "mcp__srv__tool", "input": {}},
        ],
        "tool_results": ["ra", "rb"],
    })
    _, viz_events = await _collect_events(runner, event)
    calls = _find_by_type(viz_events, "tool_call")
    assert len(calls) == 2
    assert calls[0]["payload"]["source"] == "builtin"
    assert calls[1]["payload"]["source"] == "mcp"
    assert calls[1]["payload"]["tool_call_id"] == "tc_2"


async def test_maps_step_tool_use_to_thinking() -> None:
    runner = _make_runner()
    event = LoopEvent(type="step", step=1, data={"stop_reason": "tool_use"})
    _, viz_events = await _collect_events(runner, event)
    assert len(_find_by_type(viz_events, "thinking")) == 1


async def test_maps_done_to_done() -> None:
    runner = _make_runner()
    event = LoopEvent(type="done", step=1, data={"content": "ok"})
    _, viz_events = await _collect_events(runner, event)
    assert len(_find_by_type(viz_events, "done")) >= 1


async def test_maps_error_to_error() -> None:
    runner = _make_runner()
    event = LoopEvent(type="error", step=1, data={"error": "boom"})
    _, viz_events = await _collect_events(runner, event)
    assert len(_find_by_type(viz_events, "error")) == 1


async def test_publishes_shutdown_after_loop() -> None:
    _, viz_events = await _collect_events(_make_runner())
    assert viz_events[-1]["type"] == "shutdown"


async def test_yields_original_events() -> None:
    runner = _make_runner()
    e1 = LoopEvent(type="step", step=1, data={"stop_reason": "tool_use"})
    e2 = LoopEvent(type="done", step=1, data={"content": "ok"})
    yielded, _ = await _collect_events(runner, e1, e2)
    assert yielded == [e1, e2]


async def test_publishes_error_and_shutdown_on_exception() -> None:
    runner = _make_runner()

    async def failing_gen() -> Any:
        yield LoopEvent(type="step", step=1, data={"stop_reason": "tool_use"})
        raise RuntimeError("test crash")

    q = await runner._bus.subscribe()
    with pytest.raises(RuntimeError, match="test crash"):
        async for _ in runner.wrap(failing_gen()):
            pass

    events: list[dict] = []
    while not q.empty():
        events.append(q.get_nowait())
    types = [e["type"] for e in events]
    assert "error" in types
    assert "shutdown" in types


async def test_unknown_event_type_yields_without_extra_viz() -> None:
    runner = _make_runner()

    async def gen() -> Any:
        yield LoopEvent(type="custom_unknown", step=1, data={})

    q = await runner._bus.subscribe()
    yielded: list[LoopEvent] = []
    async for event in runner.wrap(gen()):
        yielded.append(event)

    viz_events: list[dict] = []
    while not q.empty():
        viz_events.append(q.get_nowait())

    assert len(yielded) == 1
    # 启动事件(config/system_prompt/idle) + shutdown，custom_unknown 不产生额外 viz
    types = [e["type"] for e in viz_events]
    assert "config" in types
    assert "system_prompt" in types
    assert "idle" in types
    assert "shutdown" in types
    assert "thinking" not in types
    assert "tool_call" not in types


def test_build_system_prompt_payload_maps_blocks() -> None:
    """profile 模式下 blocks 非空且字段正确映射（覆盖 _build_system_prompt_payload 的非空分支）。"""
    from agent_framework.viz.agent_runner import _build_system_prompt_payload

    profile = AgentProfile(name="p", description="d", soul="my soul", identity="my id")
    loop = _make_loop(profile=profile)
    payload = _build_system_prompt_payload(loop)
    assert payload["text"]  # 非空（含 soul/identity 渲染）
    names = [b["name"] for b in payload["blocks"]]
    assert "SOUL" in names
    assert "IDENTITY" in names
    soul_block = next(b for b in payload["blocks"] if b["name"] == "SOUL")
    assert soul_block["content"] == "my soul"
    assert soul_block["source"] == "injected"
    assert soul_block["stability"] == "static"


# --- M2-T1: emit_snapshot（晚连接拉回会话级快照）---


def test_emit_snapshot_returns_config_and_system_prompt() -> None:
    runner = _make_runner()
    events = runner.emit_snapshot()
    assert [e["type"] for e in events] == ["config", "system_prompt"]
    assert all(e["session_id"] == "test-session" for e in events)
    assert events[0]["payload"]["model"] == "mock-model"
    assert isinstance(events[1]["payload"]["text"], str)
