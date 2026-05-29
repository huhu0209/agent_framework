"""Tests for A2A data models: AgentCard, A2ATask, A2AMessage, A2ATaskStatus, load_agent_card."""

import pytest

from agent_framework.a2a.models import (
    A2AMessage,
    A2ATask,
    A2ATaskStatus,
    AgentCard,
    load_agent_card,
)


class TestA2ATaskStatus:
    """A2ATaskStatus enum: five values, is_terminal property."""

    def test_status_values(self):
        assert A2ATaskStatus.PENDING == "pending"
        assert A2ATaskStatus.RUNNING == "running"
        assert A2ATaskStatus.COMPLETED == "completed"
        assert A2ATaskStatus.FAILED == "failed"
        assert A2ATaskStatus.CANCELED == "canceled"

    def test_member_count(self):
        assert len(A2ATaskStatus) == 5

    @pytest.mark.parametrize(
        "status, expected",
        [
            (A2ATaskStatus.PENDING, False),
            (A2ATaskStatus.RUNNING, False),
            (A2ATaskStatus.COMPLETED, True),
            (A2ATaskStatus.FAILED, True),
            (A2ATaskStatus.CANCELED, True),
        ],
    )
    def test_is_terminal(self, status, expected):
        assert status.is_terminal is expected


class TestAgentCard:
    """AgentCard Pydantic model: construction, serialization, defaults."""

    def test_construction_required_fields(self):
        card = AgentCard(name="test-agent", url="http://localhost:8080")
        assert card.name == "test-agent"
        assert card.url == "http://localhost:8080"

    def test_defaults(self):
        card = AgentCard(name="a", url="http://x")
        assert card.description == ""
        assert card.version == "1.0"
        assert card.capabilities == []

    def test_all_fields(self):
        card = AgentCard(
            name="agent",
            description="A test agent",
            url="http://localhost:9090",
            version="2.0",
            capabilities=["search", "translate"],
        )
        assert card.description == "A test agent"
        assert card.version == "2.0"
        assert card.capabilities == ["search", "translate"]

    def test_model_dump(self):
        card = AgentCard(name="dumper", url="http://d")
        data = card.model_dump()
        assert data["name"] == "dumper"
        assert data["url"] == "http://d"
        assert data["description"] == ""
        assert data["version"] == "1.0"
        assert data["capabilities"] == []

    def test_model_dump_roundtrip(self):
        original = AgentCard(
            name="rt",
            description="roundtrip test",
            url="http://rt",
            version="3.0",
            capabilities=["a", "b"],
        )
        restored = AgentCard(**original.model_dump())
        assert restored == original


class TestA2ATask:
    """A2ATask model: id, status, timestamps, optional result/error."""

    def test_construction(self):
        task = A2ATask(id="t1", created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
        assert task.id == "t1"
        assert task.status == A2ATaskStatus.PENDING
        assert task.result is None
        assert task.error is None

    def test_with_result(self):
        task = A2ATask(
            id="t2",
            status=A2ATaskStatus.COMPLETED,
            result="done",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:01Z",
        )
        assert task.result == "done"

    def test_with_error(self):
        task = A2ATask(
            id="t3",
            status=A2ATaskStatus.FAILED,
            error="something broke",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:01Z",
        )
        assert task.error == "something broke"


class TestA2AMessage:
    """A2AMessage model: role + text."""

    def test_construction(self):
        msg = A2AMessage(role="user", text="hello")
        assert msg.role == "user"
        assert msg.text == "hello"

    def test_model_dump(self):
        msg = A2AMessage(role="assistant", text="world")
        data = msg.model_dump()
        assert data == {"role": "assistant", "text": "world"}


class TestLoadAgentCard:
    """load_agent_card(): parse .md frontmatter text into AgentCard."""

    def test_full_frontmatter(self):
        text = """\
---
name: my-agent
description: An agent that does things
url: http://localhost:8080
version: "2.0"
capabilities: search,translate
---
Some body text here."""
        card = load_agent_card(text)
        assert card.name == "my-agent"
        assert card.description == "An agent that does things"
        assert card.url == "http://localhost:8080"
        assert card.version == "2.0"
        assert card.capabilities == ["search", "translate"]

    def test_minimal_frontmatter(self):
        text = """\
---
name: minimal
url: http://localhost:9090
---"""
        card = load_agent_card(text)
        assert card.name == "minimal"
        assert card.url == "http://localhost:9090"
        assert card.description == ""
        assert card.version == "1.0"
        assert card.capabilities == []

    def test_empty_capabilities(self):
        text = """\
---
name: cap-test
url: http://x
capabilities: ""
---"""
        card = load_agent_card(text)
        assert card.capabilities == []

    def test_no_capabilities_key(self):
        text = """\
---
name: no-cap
url: http://x
---"""
        card = load_agent_card(text)
        assert card.capabilities == []

    def test_capabilities_with_spaces(self):
        text = """\
---
name: spaced
url: http://x
capabilities: search, translate , code
---"""
        card = load_agent_card(text)
        assert card.capabilities == ["search", "translate", "code"]

    def test_missing_name_raises(self):
        text = """\
---
url: http://x
---"""
        with pytest.raises(ValueError, match="name"):
            load_agent_card(text)

    def test_missing_url_raises(self):
        text = """\
---
name: no-url
---"""
        with pytest.raises(ValueError, match="url"):
            load_agent_card(text)

    def test_empty_frontmatter_raises(self):
        text = "no frontmatter here"
        with pytest.raises(ValueError, match="name"):
            load_agent_card(text)

    def test_filename_in_error(self):
        text = "---\nurl: http://x\n---"
        with pytest.raises(ValueError, match="my-agent\\.md"):
            load_agent_card(text, filename="my-agent.md")
