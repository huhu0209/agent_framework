"""Tests for WorkerManager — worker lifecycle management."""

import pytest
from unittest.mock import MagicMock

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.orchestrator.models import WorkerSpec
from agent_framework.orchestrator.worker_agent import WorkerManager
from agent_framework.orchestrator.worker_registry import WorkerRegistry

from tests.conftest import async_iter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _done_event(text: str) -> AgentEvent:
    return AgentEvent(type="done", step=1, data={
        "content": [{"type": "text", "text": text}],
    })


def _make_mock_agent(*, output: str = "done") -> MagicMock:
    """Create a mock Agent whose run() returns a done event with the given text."""
    agent = MagicMock(spec=Agent)
    agent.run = MagicMock(return_value=async_iter([_done_event(output)]))
    return agent


def _make_factory(output: str = "done"):
    """Create a factory that returns a mock agent with the given output."""
    def factory(*, adapter, model, router, ctx):
        return _make_mock_agent(output=output)
    return factory


def _make_registry(*specs: WorkerSpec) -> WorkerRegistry:
    reg = WorkerRegistry()
    for s in specs:
        reg.register(s)
    return reg


def _make_mgr(*specs: WorkerSpec) -> WorkerManager:
    return WorkerManager(
        _make_registry(*specs),
        adapter=MagicMock(),
        model="test",
        router=MagicMock(),
        ctx=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Spawn tests
# ---------------------------------------------------------------------------

class TestWorkerManagerSpawn:
    @pytest.mark.asyncio
    async def test_spawn_returns_completed_handle(self) -> None:
        mgr = _make_mgr(WorkerSpec(
            name="researcher", description="does research", factory=_make_factory("found 3 bugs"),
        ))
        handle = await mgr.spawn("researcher", "find bugs")
        assert handle.status == "completed"
        assert "found 3 bugs" in handle.output

    @pytest.mark.asyncio
    async def test_spawn_unknown_worker_raises(self) -> None:
        mgr = _make_mgr()
        with pytest.raises(KeyError):
            await mgr.spawn("nonexistent", "task")

    @pytest.mark.asyncio
    async def test_spawn_generates_unique_ids(self) -> None:
        mgr = _make_mgr(WorkerSpec(
            name="researcher", description="does research", factory=_make_factory("ok"),
        ))
        h1 = await mgr.spawn("researcher", "task 1")
        h2 = await mgr.spawn("researcher", "task 2")
        assert h1.id != h2.id

    @pytest.mark.asyncio
    async def test_spawn_tracks_workers(self) -> None:
        mgr = _make_mgr(WorkerSpec(
            name="researcher", description="does research", factory=_make_factory("ok"),
        ))
        await mgr.spawn("researcher", "task 1")
        assert len(mgr.list_workers()) == 1


# ---------------------------------------------------------------------------
# List tests
# ---------------------------------------------------------------------------

class TestWorkerManagerList:
    def test_list_empty(self) -> None:
        mgr = _make_mgr()
        assert mgr.list_workers() == []

    @pytest.mark.asyncio
    async def test_list_filters_by_status(self) -> None:
        mgr = _make_mgr(WorkerSpec(
            name="researcher", description="does research", factory=_make_factory("ok"),
        ))
        await mgr.spawn("researcher", "task 1")
        completed = mgr.list_workers(status="completed")
        running = mgr.list_workers(status="running")
        assert len(completed) == 1
        assert len(running) == 0


# ---------------------------------------------------------------------------
# send_message tests
# ---------------------------------------------------------------------------

class TestWorkerManagerSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_resumes_completed_worker(self) -> None:
        """send_message on a completed worker creates a new agent with the follow-up."""
        mgr = _make_mgr(WorkerSpec(
            name="researcher", description="does research", factory=_make_factory("deeper results"),
        ))
        h1 = await mgr.spawn("researcher", "initial task")
        assert h1.status == "completed"

        h2 = await mgr.send_message(h1.id, "go deeper")
        assert h2.status == "completed"
        assert "deeper results" in h2.output
        assert h2.id != h1.id  # new handle for the continuation

    @pytest.mark.asyncio
    async def test_send_message_unknown_id_raises(self) -> None:
        mgr = _make_mgr()
        with pytest.raises(KeyError):
            await mgr.send_message("w_nonexistent", "msg")


# ---------------------------------------------------------------------------
# Failure tests
# ---------------------------------------------------------------------------

class TestWorkerManagerFailure:
    @pytest.mark.asyncio
    async def test_spawn_captures_worker_error(self) -> None:
        def failing_factory(*, adapter, model, router, ctx):
            agent = MagicMock(spec=Agent)
            error_event = AgentEvent(type="error", step=1, data={"error": "worker crashed"})
            agent.run = MagicMock(return_value=async_iter([error_event]))
            return agent

        mgr = _make_mgr(WorkerSpec(
            name="bad_worker", description="crashes", factory=failing_factory,
        ))
        handle = await mgr.spawn("bad_worker", "do something")
        assert handle.status == "failed"
        assert "worker crashed" in handle.error
