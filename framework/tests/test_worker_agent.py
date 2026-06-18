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
    """Create a mock Agent whose run() returns a done event with the given text.

    E2: run 用 side_effect，每次调用返回新 async_iter（spawn + resume 多次调用）。
    """
    agent = MagicMock(spec=Agent)
    agent.run = MagicMock(side_effect=lambda *a, **kw: async_iter([_done_event(output)]))
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
        """E2: send_message on a completed worker resumes on the same agent."""
        mgr = _make_mgr(WorkerSpec(
            name="researcher", description="does research", factory=_make_factory("deeper results"),
        ))
        h1 = await mgr.spawn("researcher", "initial task")
        assert h1.status == "completed"

        h2 = await mgr.send_message(h1.id, "go deeper")
        assert h2.status == "completed"
        assert "deeper results" in h2.output
        assert h2.id == h1.id  # E2: 真 resume，worker_id 不变（原为 != spawn 新 id）

    @pytest.mark.asyncio
    async def test_send_message_resumes_same_agent_with_resume_kwarg(self) -> None:
        """E2: send_message 在原 agent 上 run(resume=True)，不 spawn 新 agent。"""
        created: list = []

        def factory(*, adapter, model, router, ctx):
            agent = _make_mock_agent(output="resumed output")
            created.append(agent)
            return agent

        mgr = _make_mgr(WorkerSpec(name="r", description="r", factory=factory))
        h1 = await mgr.spawn("r", "initial")
        assert len(created) == 1
        original_agent = created[0]

        h2 = await mgr.send_message(h1.id, "follow up")

        assert len(created) == 1  # E2: 没创建新 agent
        assert original_agent.run.call_count == 2  # spawn + resume
        # 第二次调用（send_message）应带 resume=True
        second_call = original_agent.run.call_args_list[1]
        assert second_call.kwargs.get("resume") is True

    @pytest.mark.asyncio
    async def test_spawn_evicts_oldest_agent_beyond_lru_limit(self) -> None:
        """E2: 超过 LRU 上限淘汰最旧 agent，其 send_message 报错。"""
        from agent_framework.orchestrator.worker_agent import _MAX_LIVE_AGENTS
        mgr = _make_mgr(WorkerSpec(
            name="r", description="r", factory=_make_factory("ok"),
        ))
        ids = []
        for i in range(_MAX_LIVE_AGENTS + 1):
            h = await mgr.spawn("r", f"task {i}")
            ids.append(h.id)

        # 第一个 worker 的 agent 被淘汰
        assert ids[0] not in mgr._agents
        with pytest.raises(RuntimeError, match="回收"):
            await mgr.send_message(ids[0], "msg")
        # 最新 worker 仍可 resume
        h_last = await mgr.send_message(ids[-1], "msg")
        assert h_last.status == "completed"

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

    @pytest.mark.asyncio
    async def test_spawn_timeout_marks_failed(self, monkeypatch) -> None:
        """H-E3: worker 执行超时返回 failed，不永久挂起。"""
        import asyncio
        from agent_framework.orchestrator import worker_agent
        monkeypatch.setattr(worker_agent, "_DEFAULT_TIMEOUT", 0.1, raising=False)

        async def hanging_events():  # async generator，永不产出事件
            await asyncio.sleep(10)
            yield

        def hanging_factory(*, adapter, model, router, ctx):
            agent = MagicMock(spec=Agent)
            agent.run = MagicMock(side_effect=lambda *a, **kw: hanging_events())
            return agent

        mgr = _make_mgr(WorkerSpec(
            name="slow_worker", description="hangs", factory=hanging_factory,
        ))
        # wait_for 包裹防测试 hang（_DEFAULT_TIMEOUT 实现后 spawn 自己 0.1s 超时）
        handle = await asyncio.wait_for(mgr.spawn("slow_worker", "do something"), timeout=3)
        assert handle.status == "failed"
        assert "超时" in (handle.error or "")
