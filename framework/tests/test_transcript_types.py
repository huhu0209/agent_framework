"""TranscriptEvent 类型测试。"""

import time

from agent_framework.transcript.types import TranscriptEvent, TranscriptEventType


def test_event_type_is_enum():
    assert TranscriptEventType.SYSTEM == "system"
    assert TranscriptEventType.USER == "user"
    assert TranscriptEventType.ASSISTANT == "assistant"
    assert TranscriptEventType.TOOL_RESULT == "tool_result"


def test_user_event():
    ev = TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hello")
    assert ev.type == "user"
    assert ev.content == "hello"
    assert ev.tool_call_id is None


def test_assistant_event():
    blocks = [{"type": "text", "text": "hi"}]
    ev = TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0, content=blocks)
    assert ev.type == "assistant"
    assert ev.content == blocks


def test_tool_result_event():
    ev = TranscriptEvent(
        type=TranscriptEventType.TOOL_RESULT,
        timestamp=3.0,
        content="file contents",
        tool_call_id="tc_1",
        tool_name="read_file",
    )
    assert ev.tool_call_id == "tc_1"
    assert ev.tool_name == "read_file"
    assert ev.content == "file contents"


def test_system_event():
    ev = TranscriptEvent(type=TranscriptEventType.SYSTEM, timestamp=0.0, content="system prompt")
    assert ev.type == "system"
    assert ev.content == "system prompt"
