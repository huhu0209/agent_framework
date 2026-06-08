"""TranscriptReader 测试。"""

import json
from pathlib import Path

from agent_framework.llm.types import AssistantMessage, TextBlock, ToolMessage, UserMessage
from agent_framework.transcript.reader import TranscriptReader
from agent_framework.transcript.types import TranscriptEvent, TranscriptEventType
from agent_framework.transcript.writer import TranscriptWriter


def _write_events(tmp_path: Path, events: list[TranscriptEvent]) -> Path:
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)
    for ev in events:
        writer.write(ev)
    writer.close()
    return path


def test_events_returns_all_events(tmp_path: Path):
    path = _write_events(tmp_path, [
        TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hi"),
        TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0, content=[{"type": "text", "text": "hello"}]),
    ])
    reader = TranscriptReader(path)
    events = list(reader.events())
    assert len(events) == 2
    assert events[0].type == TranscriptEventType.USER
    assert events[0].content == "hi"
    assert events[1].type == TranscriptEventType.ASSISTANT


def test_to_messages_simple_conversation(tmp_path: Path):
    path = _write_events(tmp_path, [
        TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hi"),
        TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0,
                        content=[{"type": "text", "text": "hello"}]),
    ])
    reader = TranscriptReader(path)
    messages = reader.to_messages()

    assert len(messages) == 2
    assert isinstance(messages[0], UserMessage)
    assert messages[0].content[0].text == "hi"
    assert isinstance(messages[1], AssistantMessage)
    assert messages[1].content[0].text == "hello"


def test_to_messages_with_tool_use(tmp_path: Path):
    path = _write_events(tmp_path, [
        TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="read test.txt"),
        TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0, content=[
            {"type": "text", "text": "let me read that"},
            {"type": "tool_use", "id": "tc_1", "name": "read_file", "input": {"path": "test.txt"}},
        ]),
        TranscriptEvent(type=TranscriptEventType.TOOL_RESULT, timestamp=3.0,
                        content="file contents", tool_call_id="tc_1", tool_name="read_file"),
        TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=4.0,
                        content=[{"type": "text", "text": "here is the file"}]),
    ])
    reader = TranscriptReader(path)
    messages = reader.to_messages()

    assert len(messages) == 4
    assert isinstance(messages[0], UserMessage)
    assert isinstance(messages[1], AssistantMessage)
    assert len(messages[1].content) == 2
    assert messages[1].content[0].text == "let me read that"
    assert messages[1].content[1].name == "read_file"
    assert isinstance(messages[2], ToolMessage)
    assert messages[2].tool_call_id == "tc_1"
    assert messages[2].content == "file contents"
    assert isinstance(messages[3], AssistantMessage)


def test_to_messages_skips_system_events(tmp_path: Path):
    path = _write_events(tmp_path, [
        TranscriptEvent(type=TranscriptEventType.SYSTEM, timestamp=0.0, content="system prompt"),
        TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hi"),
        TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0,
                        content=[{"type": "text", "text": "hello"}]),
    ])
    reader = TranscriptReader(path)
    messages = reader.to_messages()
    assert len(messages) == 2
    assert not any(m.role == "system" for m in messages)


def test_events_empty_file(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    reader = TranscriptReader(path)
    assert list(reader.events()) == []


def test_to_messages_empty_file(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    reader = TranscriptReader(path)
    assert reader.to_messages() == []


async def test_round_trip_load_messages(tmp_path: Path):
    """写 transcript → to_messages() → load_messages() → resume 运行。"""
    from agent_framework.agents.agent_loop import AgentLoop
    from agent_framework.tools.registry import ToolRegistry
    from agent_framework.tools.router import ToolRouter
    from agent_framework.tools.types import ToolUseContext
    from agent_framework.llm.types import (
        CompletionResult, StopReason, UsageStats, ProviderInfo,
    )
    from unittest.mock import AsyncMock
    from agent_framework.llm.base import ILLMAdapter

    # 1. 写一个简单的 transcript
    path = _write_events(tmp_path, [
        TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hello"),
        TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0,
                        content=[{"type": "text", "text": "hi there"}]),
    ])

    # 2. 读取历史
    reader = TranscriptReader(path)
    messages = reader.to_messages()
    assert len(messages) == 2

    # 3. 新 loop，load_messages
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock",
    )
    adapter.complete.return_value = CompletionResult(
        id="test", model="mock",
        content=[TextBlock(text="welcome back")],
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(),
    )
    loop = AgentLoop(
        adapter=adapter, model="mock",
        router=ToolRouter(ToolRegistry()), ctx=ToolUseContext(),
    )
    loop.load_messages(messages)

    # 4. resume 运行
    events = []
    async for ev in loop.run("continue", resume=True):
        events.append(ev)
    assert len(events) >= 1

    # resume=True 时 _messages 已有 [SystemMessage, UserMessage, AssistantMessage, UserMessage]
    call_args = adapter.complete.call_args
    config = call_args[0][0]
    assert len(config.messages) == 4  # system + user + assistant + new user
