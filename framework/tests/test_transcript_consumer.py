"""TranscriptConsumer 测试。"""

from pathlib import Path
from typing import Any

import pytest

from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.transcript.consumer import TranscriptConsumer
from agent_framework.transcript.reader import TranscriptReader
from agent_framework.transcript.types import TranscriptEventType
from agent_framework.transcript.writer import TranscriptWriter


async def _run_events(*loop_events: LoopEvent):
    for ev in loop_events:
        yield ev


def _step_event(step: int = 1, stop_reason: str = "end_turn",
                content: list[dict[str, Any]] | None = None) -> LoopEvent:
    return LoopEvent(
        type="step", step=step,
        data={"stop_reason": stop_reason, "content": content or [{"type": "text", "text": "hi"}]},
    )


def _tool_result_event(step: int = 1) -> LoopEvent:
    return LoopEvent(
        type="tool_result", step=step,
        data={
            "tool_calls": [{"id": "tc_1", "name": "read_file", "input": {"path": "x.txt"}}],
            "tool_results": ["file contents"],
        },
    )


def _done_event(step: int = 1) -> LoopEvent:
    return LoopEvent(
        type="done", step=step,
        data={"content": [{"type": "text", "text": "done"}]},
    )


async def test_wrap_records_user_and_assistant(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)
    consumer = TranscriptConsumer(writer)

    events_in = [
        _step_event(content=[{"type": "text", "text": "hello"}]),
        _done_event(),
    ]

    collected = []
    async for ev in consumer.wrap(_run_events(*events_in), "user msg"):
        collected.append(ev)

    writer.close()

    assert len(collected) == 2
    assert collected[0].type == "step"
    assert collected[1].type == "done"

    reader = TranscriptReader(path)
    transcript = list(reader.events())
    assert len(transcript) == 2
    assert transcript[0].type == TranscriptEventType.USER
    assert transcript[0].content == "user msg"
    assert transcript[1].type == TranscriptEventType.ASSISTANT


async def test_wrap_records_tool_result(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)
    consumer = TranscriptConsumer(writer)

    events_in = [
        _step_event(stop_reason="tool_use", content=[
            {"type": "tool_use", "id": "tc_1", "name": "read_file", "input": {"path": "x.txt"}},
        ]),
        _tool_result_event(),
        _step_event(step=2, content=[{"type": "text", "text": "final answer"}]),
        _done_event(step=2),
    ]

    async for _ in consumer.wrap(_run_events(*events_in), "read x.txt"):
        pass
    writer.close()

    reader = TranscriptReader(path)
    transcript = list(reader.events())

    types = [t.type for t in transcript]
    assert types == [
        TranscriptEventType.USER,
        TranscriptEventType.ASSISTANT,
        TranscriptEventType.TOOL_RESULT,
        TranscriptEventType.ASSISTANT,
    ]

    tool_ev = transcript[2]
    assert tool_ev.tool_call_id == "tc_1"
    assert tool_ev.tool_name == "read_file"
    assert tool_ev.content == "file contents"


async def test_wrap_with_system_prompt(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)
    consumer = TranscriptConsumer(writer, system_prompt="you are helpful")

    async for _ in consumer.wrap(_run_events(_step_event()), "hi"):
        pass
    writer.close()

    reader = TranscriptReader(path)
    transcript = list(reader.events())
    assert len(transcript) == 3
    assert transcript[0].type == TranscriptEventType.SYSTEM
    assert transcript[0].content == "you are helpful"


async def test_wrap_skips_error_and_max_steps(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)
    consumer = TranscriptConsumer(writer)

    events_in = [
        _step_event(content=[{"type": "text", "text": "hi"}]),
        LoopEvent(type="error", step=1, data={"error": "something broke"}),
        LoopEvent(type="max_steps", step=10, data={}),
    ]

    async for _ in consumer.wrap(_run_events(*events_in), "msg"):
        pass
    writer.close()

    reader = TranscriptReader(path)
    transcript = list(reader.events())
    types = [t.type for t in transcript]
    assert len(transcript) == 2
    assert TranscriptEventType.USER in types
    assert TranscriptEventType.ASSISTANT in types
