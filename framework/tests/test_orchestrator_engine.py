"""OrchestratorEngine 测试。"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.plan_and_solve import PlanAndSolveAgent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.orchestrator.engine import OrchestratorEngine
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


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


def _make_mock_adapter_with_plan(plan_text: str) -> AsyncMock:
    """创建返回含 <plan> 标签响应的 mock adapter。"""
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text=plan_text)],
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


class TestAssessComplexity:
    """复杂度评估测试。"""

    def test_assess_complexity_simple(self) -> None:
        """ORCH-02: 任务字符数 <= 200 返回 simple。"""
        adapter = _make_mock_adapter_with_text("")
        engine = _make_engine(adapter)
        assert engine._assess_complexity("短任务") == "simple"

    def test_assess_complexity_complex(self) -> None:
        """ORCH-02: 任务字符数 > 200 返回 complex。"""
        adapter = _make_mock_adapter_with_text("")
        engine = _make_engine(adapter)
        long_task = "a" * 201
        assert engine._assess_complexity(long_task) == "complex"

    def test_assess_complexity_threshold_configurable(self) -> None:
        """D-01: 自定义阈值生效。"""
        adapter = _make_mock_adapter_with_text("")
        engine = _make_engine(adapter, complexity_threshold=50)
        # 60 chars > 50 threshold -> complex
        assert engine._assess_complexity("a" * 60) == "complex"
        # 40 chars <= 50 threshold -> simple
        assert engine._assess_complexity("a" * 40) == "simple"


class TestAgentSelection:
    """Agent 路由测试。"""

    @pytest.mark.asyncio
    async def test_simple_task_routes_to_agent_loop(self) -> None:
        """ORCH-03: 简单任务路由到 AgentLoop，事件正确转发。"""
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
    async def test_complex_task_routes_to_plan_and_solve(self) -> None:
        """ORCH-03: 复杂任务路由到 PlanAndSolveAgent，事件正确转发。"""
        adapter = _make_mock_adapter_with_plan(
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
        # Agent was created
        MockPnS.assert_called_once()


class TestAgentCountLimit:
    """Agent 数量上限测试。"""

    @pytest.mark.asyncio
    async def test_agent_count_limit_at_three(self) -> None:
        """ORCH-04: Agent 实例数上限为 3，第 4 次调用返回 error 事件。"""
        adapter = _make_mock_adapter_with_text("完成")

        mock_loop = MagicMock()
        mock_loop.run = MagicMock(return_value=_async_iter([
            AgentEvent(type="done", step=1, data={}),
        ]))

        with patch("agent_framework.agents.agent_loop.AgentLoop", return_value=mock_loop):
            engine = _make_engine(adapter)

            # First 3 calls succeed
            for _ in range(3):
                events = await _collect_events(engine, "任务")
                assert events[0].data["complexity"] == "simple"

            # 4th call: should get error event
            events = await _collect_events(engine, "任务")
            error_events = [e for e in events if e.type == "error"]
            assert len(error_events) == 1
            assert "上限" in error_events[0].data["error"]


class TestImplementsAgentABC:
    """Agent ABC 兼容性测试。"""

    def test_implements_agent_abc(self) -> None:
        """ORCH-01: OrchestratorEngine 是 Agent 子类。"""
        assert issubclass(OrchestratorEngine, Agent)
