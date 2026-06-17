"""VizEvent 单元测试 — EVNT-04。"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from agent_framework.viz.viz_event import VizEvent, VizEventType


def test_viz_event_creation() -> None:
    event = VizEvent(
        type="thinking",
        agent="cat",
        payload={"step": 1},
        timestamp=1234.5,
    )
    assert event.type == "thinking"
    assert event.agent == "cat"
    assert event.payload == {"step": 1}
    assert event.timestamp == 1234.5


def test_viz_event_json_serialization() -> None:
    event = VizEvent(
        type="tool_call",
        agent="dog",
        payload={"tool": "search"},
        timestamp=9999.0,
    )
    raw = event.model_dump_json()
    data = json.loads(raw)
    assert data["type"] == "tool_call"
    assert data["agent"] == "dog"
    assert data["payload"] == {"tool": "search"}
    assert "timestamp" in data


@pytest.mark.parametrize(
    "valid_type",
    ["idle", "thinking", "tool_call", "tool_result", "done", "error", "shutdown"],
)
def test_viz_event_valid_types(valid_type: VizEventType) -> None:
    event = VizEvent(type=valid_type, agent="a", payload={}, timestamp=0.0)
    assert event.type == valid_type


def test_viz_event_type_invalid() -> None:
    with pytest.raises(ValidationError):
        VizEvent(type="invalid", agent="a", payload={}, timestamp=0.0)


from agent_framework.viz.viz_event import (
    ConfigPayload,
    PromptBlockPayload,
    SystemPromptPayload,
)


@pytest.mark.parametrize(
    "valid_type",
    ["idle", "thinking", "tool_call", "tool_result", "done", "error", "shutdown",
     "config", "system_prompt", "memory"],
)
def test_viz_event_valid_types_extended(valid_type: VizEventType) -> None:
    event = VizEvent(type=valid_type, agent="a", payload={}, timestamp=0.0)
    assert event.type == valid_type


def test_viz_event_carries_session_id() -> None:
    event = VizEvent(
        type="config", agent="cat", session_id="abc123",
        payload={"model": "x"}, timestamp=1.0,
    )
    assert event.session_id == "abc123"


def test_viz_event_session_id_defaults_empty() -> None:
    event = VizEvent(type="idle", agent="a", payload={}, timestamp=0.0)
    assert event.session_id == ""


def test_config_payload_contract() -> None:
    p = ConfigPayload(model="m", max_steps=10, tools=["read_file"])
    dumped = p.model_dump()
    assert dumped == {
        "model": "m", "max_steps": 10,
        "profile": None, "permission_mode": None, "tools": ["read_file"],
    }


def test_system_prompt_payload_contract() -> None:
    p = SystemPromptPayload(
        text="hi",
        blocks=[PromptBlockPayload(name="SOUL", content="x", source="injected", stability="static")],
    )
    assert p.text == "hi"
    assert p.blocks[0].name == "SOUL"
    assert p.blocks[0].source == "injected"
