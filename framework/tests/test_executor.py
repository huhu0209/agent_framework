"""DAGExecutor 测试 — P1 串行执行。"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.orchestrator.executor import DAGExecutor
from agent_framework.orchestrator.models import SubTask, WorkerSpec
from agent_framework.orchestrator.worker_registry import WorkerRegistry
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

from tests.conftest import AsyncIter, async_iter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_agent(*, events: list[AgentEvent]) -> MagicMock:
    """Create a mock Agent whose run() returns the given events."""
    agent = MagicMock(spec=Agent)
    agent.run = MagicMock(return_value=async_iter(events))
    return agent


def _make_executor(registry: WorkerRegistry) -> DAGExecutor:
    """Create a DAGExecutor with mock adapter/router/ctx."""
    adapter = AsyncMock(spec=ILLMAdapter)
    tool_registry = ToolRegistry()
    router = ToolRouter(tool_registry)
    ctx = ToolUseContext()
    return DAGExecutor(
        worker_registry=registry,
        adapter=adapter,
        model="mock-model",
        router=router,
        ctx=ctx,
    )


async def _collect_events(executor: DAGExecutor, plan: list[SubTask]) -> list[AgentEvent]:
    return [event async for event in executor.execute(plan)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSerialExecution:
    """串行执行测试。"""

    @pytest.mark.asyncio
    async def test_single_subtask(self) -> None:
        """单个 subtask: 产生 worker_start + worker_done 两个事件。"""
        mock_agent = _make_mock_agent(events=[
            AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "结果A"}]}),
        ])

        factory = MagicMock(return_value=mock_agent)
        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="searcher", description="搜索", factory=factory))

        executor = _make_executor(registry)
        plan = [SubTask(id="t1", worker="searcher", prompt="搜索X")]

        events = await _collect_events(executor, plan)

        assert len(events) == 2
        assert events[0].type == "worker_start"
        assert events[0].data["subtask_id"] == "t1"
        assert events[0].data["worker"] == "searcher"
        assert events[0].data["prompt"] == "搜索X"

        assert events[1].type == "worker_done"
        assert events[1].data["subtask_id"] == "t1"
        assert events[1].data["output"] == "结果A"
        assert events[1].data["success"] is True
        assert events[1].data["error"] is None

    @pytest.mark.asyncio
    async def test_multiple_subtasks_serial(self) -> None:
        """多个 subtask 按顺序串行执行。"""
        agent_a = _make_mock_agent(events=[
            AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "结果A"}]}),
        ])
        agent_b = _make_mock_agent(events=[
            AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "结果B"}]}),
        ])

        factory_a = MagicMock(return_value=agent_a)
        factory_b = MagicMock(return_value=agent_b)

        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="searcher", description="搜索", factory=factory_a))
        registry.register(WorkerSpec(name="analyzer", description="分析", factory=factory_b))

        executor = _make_executor(registry)
        plan = [
            SubTask(id="t1", worker="searcher", prompt="搜索X", depends_on=()),
            SubTask(id="t2", worker="analyzer", prompt="分析Y", depends_on=("t1",)),
        ]

        events = await _collect_events(executor, plan)

        # 2 subtasks * (worker_start + worker_done) = 4 events
        assert len(events) == 4

        # Order: t1 start, t1 done, t2 start, t2 done
        assert events[0].type == "worker_start"
        assert events[0].data["subtask_id"] == "t1"

        assert events[1].type == "worker_done"
        assert events[1].data["output"] == "结果A"

        assert events[2].type == "worker_start"
        assert events[2].data["subtask_id"] == "t2"

        assert events[3].type == "worker_done"
        assert events[3].data["output"] == "结果B"

    @pytest.mark.asyncio
    async def test_out_of_order_plan_raises(self) -> None:
        """依赖未在前面执行 → ValueError。"""
        mock_agent = _make_mock_agent(events=[
            AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "ok"}]}),
        ])
        factory = MagicMock(return_value=mock_agent)
        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="a", description="A", factory=factory))
        registry.register(WorkerSpec(name="b", description="B", factory=factory))

        executor = _make_executor(registry)
        # t2 depends on t1, but t2 comes first in the list
        plan = [
            SubTask(id="t2", worker="b", prompt="B", depends_on=("t1",)),
            SubTask(id="t1", worker="a", prompt="A", depends_on=()),
        ]

        with pytest.raises(ValueError, match="topological"):
            await _collect_events(executor, plan)


class TestFailureFastFail:
    """异常与空输出测试。"""

    @pytest.mark.asyncio
    async def test_worker_raises_exception(self) -> None:
        """Worker 抛异常 -> orchestrator_error 事件 + 快速失败。"""
        failing_agent = MagicMock(spec=Agent)
        failing_agent.run = MagicMock(side_effect=RuntimeError("LLM 挂了"))

        factory = MagicMock(return_value=failing_agent)
        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="searcher", description="搜索", factory=factory))

        executor = _make_executor(registry)
        plan = [
            SubTask(id="t1", worker="searcher", prompt="搜索X"),
            SubTask(id="t2", worker="searcher", prompt="搜索Y"),
        ]

        events = await _collect_events(executor, plan)

        # worker_start + worker_done(success=False) + orchestrator_error
        # t2 should NOT execute (fast fail)
        assert len(events) == 3

        assert events[0].type == "worker_start"
        assert events[1].type == "worker_done"
        assert events[1].data["success"] is False
        assert "LLM 挂了" in events[1].data["error"]

        assert events[2].type == "orchestrator_error"
        assert "searcher" in events[2].data["error"]
        assert events[2].data["subtask_id"] == "t1"

    @pytest.mark.asyncio
    async def test_worker_empty_output_still_succeeds(self) -> None:
        """空输出不是失败 —— "没找到" 是合法回答。"""
        mock_agent = _make_mock_agent(events=[
            AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": ""}]}),
        ])

        factory = MagicMock(return_value=mock_agent)
        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="searcher", description="搜索", factory=factory))

        executor = _make_executor(registry)
        plan = [SubTask(id="t1", worker="searcher", prompt="搜索不存在的东西")]

        events = await _collect_events(executor, plan)

        assert len(events) == 2
        assert events[1].type == "worker_done"
        assert events[1].data["success"] is True
        assert events[1].data["output"] == ""

    @pytest.mark.asyncio
    async def test_error_event_marks_failure(self) -> None:
        """Agent 产出 error 事件 → worker_done(success=False)。"""
        error_agent = MagicMock(spec=Agent)
        error_agent.run = MagicMock(return_value=async_iter([
            AgentEvent(type="error", step=0, data={"error": "内部错误"}),
        ]))

        factory = MagicMock(return_value=error_agent)
        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="worker", description="W", factory=factory))

        executor = _make_executor(registry)
        plan = [SubTask(id="t1", worker="worker", prompt="do")]

        events = await _collect_events(executor, plan)

        assert len(events) == 3
        assert events[1].type == "worker_done"
        assert events[1].data["success"] is False
        assert "内部错误" in events[1].data["error"]


class TestEventOrder:
    """事件顺序测试。"""

    @pytest.mark.asyncio
    async def test_event_order_within_subtask(self) -> None:
        """worker_start 一定在 worker_done 之前。"""
        mock_agent = _make_mock_agent(events=[
            AgentEvent(type="step", step=1, data={"content": []}),
            AgentEvent(type="done", step=2, data={"content": [{"type": "text", "text": "结果"}]}),
        ])

        factory = MagicMock(return_value=mock_agent)
        registry = WorkerRegistry()
        registry.register(WorkerSpec(name="searcher", description="搜索", factory=factory))

        executor = _make_executor(registry)
        plan = [SubTask(id="t1", worker="searcher", prompt="搜索")]

        events = await _collect_events(executor, plan)

        types = [e.type for e in events]
        start_idx = types.index("worker_start")
        done_idx = types.index("worker_done")
        assert start_idx < done_idx
