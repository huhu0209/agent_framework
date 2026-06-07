"""OrchestratorEngine 测试 — 三级退化链。"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.orchestrator.engine import OrchestratorEngine
from agent_framework.orchestrator.models import WorkerSpec
from agent_framework.orchestrator.worker_registry import WorkerRegistry
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_adapter_with_text(text: str) -> AsyncMock:
    """创建返回纯文本响应的 mock adapter。"""
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(input_tokens=100, output_tokens=50),
    )
    return adapter


def _make_engine(adapter: AsyncMock, **kwargs) -> OrchestratorEngine:
    """创建 OrchestratorEngine 实例。"""
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    return OrchestratorEngine(
        adapter=adapter,
        model="mock",
        router=router,
        ctx=ctx,
        **kwargs,
    )


async def _collect_events(engine: OrchestratorEngine, message: str) -> list[AgentEvent]:
    """收集 engine.run() 产生的所有事件。"""
    return [event async for event in engine.run(message)]


class _AsyncIter:
    """Helper to create async iterables from a list."""

    def __init__(self, items: list[AgentEvent]) -> None:
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self) -> AgentEvent:
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


def _async_iter(items: list[AgentEvent]) -> _AsyncIter:
    """创建异步迭代器。"""
    return _AsyncIter(items)


def _register_dummy_worker(registry: WorkerRegistry, name: str = "dummy") -> None:
    """注册一个 dummy worker。"""
    spec = WorkerSpec(
        name=name,
        description=f"A {name} worker for testing",
        factory=lambda **kw: MagicMock(),
    )
    registry.register(spec)


# ---------------------------------------------------------------------------
# TestAssessComplexity
# ---------------------------------------------------------------------------


class TestAssessComplexity:
    """复杂度评估测试。"""

    def test_simple(self) -> None:
        """短任务 → simple。"""
        adapter = _make_mock_adapter_with_text("")
        engine = _make_engine(adapter)
        assert engine._assess_complexity("短任务") == "simple"

    def test_complex(self) -> None:
        """长任务（201 chars）→ complex。"""
        adapter = _make_mock_adapter_with_text("")
        engine = _make_engine(adapter)
        long_task = "a" * 201
        assert engine._assess_complexity(long_task) == "complex"


# ---------------------------------------------------------------------------
# TestDegradationChain
# ---------------------------------------------------------------------------


class TestDegradationChain:
    """三级退化链测试。"""

    @pytest.mark.asyncio
    async def test_simple_task_uses_agent_loop(self) -> None:
        """简单任务路由到 AgentLoop。"""
        adapter = _make_mock_adapter_with_text("完成")

        mock_loop = MagicMock()
        mock_loop.run = MagicMock(return_value=_async_iter([
            AgentEvent(type="step", step=1, data={"content": []}),
            AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "完成"}]}),
        ]))

        with patch("agent_framework.agents.agent_loop.AgentLoop", return_value=mock_loop) as MockLoop:
            engine = _make_engine(adapter)
            events = await _collect_events(engine, "简单任务")

        # First event: complexity assessment
        assert events[0].type == "step"
        assert events[0].data["complexity"] == "simple"
        assert events[0].data["task_length"] == len("简单任务")

        # Remaining events forwarded from AgentLoop with step offset
        assert events[1].type == "step"
        assert events[1].step == 2  # 1 + offset
        assert events[2].type == "done"

        MockLoop.assert_called_once()

    @pytest.mark.asyncio
    async def test_complex_no_workers_uses_plan_and_solve(self) -> None:
        """复杂任务 + 无 Workers → PlanAndSolveAgent。"""
        adapter = _make_mock_adapter_with_text(
            "<plan>\n1. 步骤一\n</plan>"
        )

        mock_pns = MagicMock()
        mock_pns.run = MagicMock(return_value=_async_iter([
            AgentEvent(type="step", step=1, data={"text": "执行步骤"}),
            AgentEvent(type="done", step=1, data={"text": "完成"}),
        ]))

        with patch("agent_framework.agents.plan_and_solve.PlanAndSolveAgent", return_value=mock_pns) as MockPnS:
            engine = _make_engine(adapter)
            long_task = "这是一个非常复杂的任务" + "，包含很多细节" * 30
            events = await _collect_events(engine, long_task)

        # First event: complexity assessment
        assert events[0].data["complexity"] == "complex"
        # PlanAndSolveAgent was created
        MockPnS.assert_called_once()

    @pytest.mark.asyncio
    async def test_complex_with_workers_uses_pipeline(self) -> None:
        """复杂任务 + 有 Workers → Decomposer → DAGExecutor 管道。"""
        # LLM returns valid decomposition XML
        adapter = _make_mock_adapter_with_text(
            '<decomposition>\n'
            '<subtask id="1" worker="dummy" depends_on="">\n'
            '  Do something\n'
            '</subtask>\n'
            '</decomposition>'
        )

        worker_registry = WorkerRegistry()
        _register_dummy_worker(worker_registry, "dummy")

        # Mock the agent created by worker factory
        mock_worker_agent = MagicMock()
        mock_worker_agent.run = MagicMock(return_value=_async_iter([
            AgentEvent(type="done", step=0, data={"content": [{"type": "text", "text": "worker output"}]}),
        ]))

        # Register worker with factory that returns our mock
        spec = WorkerSpec(
            name="dummy",
            description="A dummy worker",
            factory=lambda **kw: mock_worker_agent,
        )
        worker_registry._workers["dummy"] = spec

        engine = _make_engine(adapter, worker_registry=worker_registry)
        long_task = "这是一个非常复杂的任务" + "，包含很多细节" * 30
        events = await _collect_events(engine, long_task)

        # Verify event sequence
        types = [e.type for e in events]

        # step (complexity) → decompose_start → decompose_done → worker_start → worker_done → orchestrator_done
        assert types[0] == "step"
        assert events[0].data["complexity"] == "complex"

        assert "decompose_start" in types
        assert "decompose_done" in types
        assert "worker_start" in types
        assert "worker_done" in types
        assert "orchestrator_done" in types

        # Verify decompose_done has subtask_count
        decompose_done = next(e for e in events if e.type == "decompose_done")
        assert decompose_done.data["subtask_count"] == 1

        # Verify orchestrator_done has synthesized output
        done_event = next(e for e in events if e.type == "orchestrator_done")
        assert "synthesized_output" in done_event.data

    @pytest.mark.asyncio
    async def test_decompose_failure_degrades_to_plan_and_solve(self) -> None:
        """分解失败时自动退化为 PlanAndSolveAgent。"""
        # LLM returns unparseable text (no <decomposition> tags)
        adapter = _make_mock_adapter_with_text("This is not valid XML at all")

        worker_registry = WorkerRegistry()
        _register_dummy_worker(worker_registry, "dummy")

        mock_pns = MagicMock()
        mock_pns.run = MagicMock(return_value=_async_iter([
            AgentEvent(type="done", step=1, data={"text": "plan and solve result"}),
        ]))

        with patch("agent_framework.agents.plan_and_solve.PlanAndSolveAgent", return_value=mock_pns) as MockPnS:
            engine = _make_engine(adapter, worker_registry=worker_registry)
            long_task = "这是一个非常复杂的任务" + "，包含很多细节" * 30
            events = await _collect_events(engine, long_task)

        # Verify degraded to PlanAndSolveAgent
        MockPnS.assert_called_once()

        # Event sequence: step → decompose_start → (degrade) → done from PnS
        types = [e.type for e in events]
        assert "decompose_start" in types
        # No decompose_done since decompose failed
        assert "decompose_done" not in types
        assert "orchestrator_done" not in types
        # But we get the done event from PlanAndSolveAgent
        assert "done" in types


# ---------------------------------------------------------------------------
# TestImplementsAgentABC
# ---------------------------------------------------------------------------


class TestImplementsAgentABC:
    """Agent ABC 兼容性测试。"""

    def test_is_agent_subclass(self) -> None:
        """OrchestratorEngine 是 Agent 子类。"""
        assert issubclass(OrchestratorEngine, Agent)

    @pytest.mark.asyncio
    async def test_backward_compatible_no_registry(self) -> None:
        """不传 worker_registry 时，简单任务仍可正常工作。"""
        adapter = _make_mock_adapter_with_text("完成")

        mock_loop = MagicMock()
        mock_loop.run = MagicMock(return_value=_async_iter([
            AgentEvent(type="done", step=0, data={"content": [{"type": "text", "text": "完成"}]}),
        ]))

        with patch("agent_framework.agents.agent_loop.AgentLoop", return_value=mock_loop):
            engine = _make_engine(adapter)  # no worker_registry
            events = await _collect_events(engine, "简单任务")

        assert events[0].data["complexity"] == "simple"
        assert len(events) == 2  # step + done
