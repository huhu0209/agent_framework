"""AgentRunner 单元测试 — EVNT-05/06/07。"""

import asyncio
from typing import Any

import pytest

from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.viz.agent_runner import AgentRunner
from agent_framework.viz.event_bus import EventBus


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


async def test_maps_step_tool_use_to_thinking() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="step", step=1, data={"stop_reason": "tool_use"})
    _, viz_events = await _collect_events(runner, event)
    thinking = _find_by_type(viz_events, "thinking")
    assert len(thinking) == 1
    assert thinking[0]["payload"]["step"] == 1


async def test_maps_step_end_turn_to_done() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="step", step=1, data={"stop_reason": "end_turn"})
    _, viz_events = await _collect_events(runner, event)
    done = _find_by_type(viz_events, "done")
    assert len(done) == 1


async def test_maps_step_stop_sequence_to_done() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="step", step=1, data={"stop_reason": "stop_sequence"})
    _, viz_events = await _collect_events(runner, event)
    done = _find_by_type(viz_events, "done")
    assert len(done) == 1


async def test_maps_tool_result_to_tool_call() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="tool_result", step=1, data={"tool_calls": [], "tool_results": []})
    _, viz_events = await _collect_events(runner, event)
    tool_call = _find_by_type(viz_events, "tool_call")
    assert len(tool_call) == 1


async def test_maps_done_to_done() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="done", step=1, data={"content": "ok"})
    _, viz_events = await _collect_events(runner, event)
    done = _find_by_type(viz_events, "done")
    assert len(done) == 1


async def test_maps_error_to_error() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="error", step=1, data={"error": "boom"})
    _, viz_events = await _collect_events(runner, event)
    errors = _find_by_type(viz_events, "error")
    assert len(errors) == 1


async def test_maps_max_steps_to_error() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    event = LoopEvent(type="max_steps", step=10, data={})
    _, viz_events = await _collect_events(runner, event)
    errors = _find_by_type(viz_events, "error")
    assert len(errors) == 1


async def test_publishes_idle_before_loop() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    _, viz_events = await _collect_events(runner)
    assert viz_events[0]["type"] == "idle"


async def test_publishes_shutdown_after_loop() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    _, viz_events = await _collect_events(runner)
    assert viz_events[-1]["type"] == "shutdown"


async def test_yields_original_events() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)
    e1 = LoopEvent(type="step", step=1, data={"stop_reason": "tool_use"})
    e2 = LoopEvent(type="tool_result", step=1, data={})
    e3 = LoopEvent(type="done", step=1, data={"content": "ok"})
    yielded, _ = await _collect_events(runner, e1, e2, e3)
    assert len(yielded) == 3
    assert yielded[0] is e1
    assert yielded[1] is e2
    assert yielded[2] is e3


async def test_publishes_error_and_shutdown_on_exception() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)

    async def failing_gen() -> Any:
        yield LoopEvent(type="step", step=1, data={"stop_reason": "tool_use"})
        raise RuntimeError("test crash")

    q = await bus.subscribe()
    with pytest.raises(RuntimeError, match="test crash"):
        async for _ in runner.wrap(failing_gen()):
            pass

    events: list[dict] = []
    while not q.empty():
        events.append(q.get_nowait())

    types = [e["type"] for e in events]
    assert "error" in types
    assert "shutdown" in types


async def test_unknown_event_type_yields_without_viz() -> None:
    bus = EventBus()
    runner = AgentRunner("test", bus)

    async def gen() -> Any:
        yield LoopEvent(type="custom_unknown", step=1, data={})

    q = await bus.subscribe()
    yielded: list[LoopEvent] = []
    async for event in runner.wrap(gen()):
        yielded.append(event)

    viz_events: list[dict] = []
    while not q.empty():
        viz_events.append(q.get_nowait())

    assert len(yielded) == 1
    # only idle + shutdown, no mapping for "custom_unknown"
    mapped_types = [e["type"] for e in viz_events]
    assert "idle" in mapped_types
    assert "shutdown" in mapped_types
    assert len(mapped_types) == 2
