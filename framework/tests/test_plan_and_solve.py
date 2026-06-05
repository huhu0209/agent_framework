"""PlanAndSolveAgent 测试。"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.plan_and_solve import PlanAndSolveAgent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


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


def _make_agent(adapter: AsyncMock, **kwargs) -> PlanAndSolveAgent:
    """创建 PlanAndSolveAgent 实例。"""
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    return PlanAndSolveAgent(
        adapter=adapter,
        model="mock",
        router=router,
        ctx=ctx,
        **kwargs,
    )


async def _collect_events(agent: PlanAndSolveAgent, message: str) -> list[AgentEvent]:
    """收集 agent.run() 产生的所有事件。"""
    return [event async for event in agent.run(message)]


class TestPlanAndSolveAgent:
    """PlanAndSolveAgent 测试套件。"""

    def test_inherits_agent(self) -> None:
        """PLAN-01: PlanAndSolveAgent 继承 Agent。"""
        assert issubclass(PlanAndSolveAgent, Agent)

    @pytest.mark.asyncio
    async def test_plan_generation(self) -> None:
        """PLAN-02: 生成计划阶段调用 LLM 并产出 PlanItem 列表。"""
        adapter = _make_mock_adapter_with_plan(
            "<plan>\n1. 第一步\n2. 第二步\n3. 第三步\n</plan>"
        )
        agent = _make_agent(adapter)

        # Mock AgentLoop to return simple done events
        with patch("agent_framework.agents.plan_and_solve.AgentLoop") as MockLoop:
            mock_loop = AsyncMock(spec=PlanAndSolveAgent)
            mock_loop.run.return_value = _async_iter([
                AgentEvent(type="step", step=1, data={"content": [{"type": "text", "text": "输出"}]}),
                AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "步骤完成"}]}),
            ])
            MockLoop.return_value = mock_loop

            events = await _collect_events(agent, "完成一个三步任务")

        # Should have step events (3 steps) + done event
        types = [e.type for e in events]
        assert "done" in types
        # Plan generation LLM call was made
        adapter.complete.assert_called()

    @pytest.mark.asyncio
    async def test_empty_plan_fallback(self) -> None:
        """PLAN-05: 空计划 fallback 到直接 ReAct 执行。"""
        adapter = _make_mock_adapter_with_text("这是一个没有计划的回答")

        agent = _make_agent(adapter)

        # Mock AgentLoop for fallback path
        with patch("agent_framework.agents.plan_and_solve.AgentLoop") as MockLoop:
            mock_loop = AsyncMock(spec=PlanAndSolveAgent)
            mock_loop.run.return_value = _async_iter([
                AgentEvent(type="step", step=1, data={"content": [{"type": "text", "text": "直接执行"}]}),
                AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "完成"}]}),
            ])
            MockLoop.return_value = mock_loop

            events = await _collect_events(agent, "简单问题")

        # Should have fallback step event + AgentLoop events
        types = [e.type for e in events]
        # First event should be the fallback notification
        assert events[0].data.get("text") == "无法生成计划，回退到直接执行"
        # Should still have done from fallback AgentLoop
        assert "done" in types

    def test_is_step_failed(self) -> None:
        """步骤失败检测测试。"""
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)

        # Empty string → failed
        assert agent._is_step_failed("") is True
        # Whitespace only → failed
        assert agent._is_step_failed("   ") is True
        # Contains error marker → failed
        assert agent._is_step_failed("[子代理错误] something went wrong") is True
        # Normal output → not failed
        assert agent._is_step_failed("正常执行结果") is False

    @pytest.mark.asyncio
    async def test_drift_replan(self) -> None:
        """PLAN-04: 偏离检测触发重新规划。"""
        # First call: generate plan, second call: replan with new plan,
        # third call: normal plan
        plan_text = "<plan>\n1. 步骤一\n</plan>"
        adapter = _make_mock_adapter_with_plan(plan_text)

        agent = _make_agent(adapter)

        call_count = 0

        with patch("agent_framework.agents.plan_and_solve.AgentLoop") as MockLoop:
            mock_loop = AsyncMock()

            def make_run_response():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First step execution: returns error (triggers drift via [子代理错误])
                    return _async_iter([
                        AgentEvent(type="error", step=1, data={"error": "something failed"}),
                    ])
                else:
                    # After replan: normal execution
                    return _async_iter([
                        AgentEvent(type="step", step=1, data={}),
                        AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "重新规划后完成"}]}),
                    ])

            mock_loop.run = lambda prompt: make_run_response()
            MockLoop.return_value = mock_loop

            events = await _collect_events(agent, "会偏离的任务")

        # Should have replan notification event
        texts = [e.data.get("text", "") for e in events if e.type == "step"]
        has_replan = any("重新规划" in t for t in texts)
        assert has_replan

    @pytest.mark.asyncio
    async def test_max_replans_exceeded(self) -> None:
        """PLAN-04: 偏离次数达到上限后返回 error 事件。"""
        plan_text = "<plan>\n1. 步骤一\n</plan>"
        adapter = _make_mock_adapter_with_plan(plan_text)
        agent = _make_agent(adapter, max_replans=2)

        with patch("agent_framework.agents.plan_and_solve.AgentLoop") as MockLoop:
            mock_loop = AsyncMock()

            # All executions return error → always drift
            mock_loop.run = lambda prompt: _async_iter([
                AgentEvent(type="error", step=1, data={"error": "failed"}),
            ])
            MockLoop.return_value = mock_loop

            events = await _collect_events(agent, "持续偏离的任务")

        # Should end with error event
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert "上限" in error_events[0].data.get("error_message", "")

    @pytest.mark.asyncio
    async def test_step_isolation(self) -> None:
        """PLAN-03: 步骤间不累积 context，step_prompt 仅含原始任务+步骤描述+前序摘要。"""
        plan_text = "<plan>\n1. 第一步\n2. 第二步\n</plan>"
        adapter = _make_mock_adapter_with_plan(plan_text)
        agent = _make_agent(adapter)

        captured_prompts: list[str] = []

        with patch("agent_framework.agents.plan_and_solve.AgentLoop") as MockLoop:
            mock_loop = AsyncMock()

            def capture_and_respond(prompt: str):
                captured_prompts.append(prompt)
                return _async_iter([
                    AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "输出"}]}),
                ])

            mock_loop.run = capture_and_respond
            MockLoop.return_value = mock_loop

            events = await _collect_events(agent, "原始任务描述")

        assert len(captured_prompts) == 2
        # First prompt: original task + step 1, no prior summary
        assert "原始任务" in captured_prompts[0]
        assert "第一步" in captured_prompts[0]
        assert "前序步骤摘要" not in captured_prompts[0]

        # Second prompt: original task + step 2 + prior summary
        assert "原始任务" in captured_prompts[1]
        assert "第二步" in captured_prompts[1]
        assert "前序步骤摘要" in captured_prompts[1]

    @pytest.mark.asyncio
    async def test_full_execution(self) -> None:
        """完整三步计划正常执行，最终返回 done 事件。"""
        plan_text = "<plan>\n1. 步骤一\n2. 步骤二\n3. 步骤三\n</plan>"
        adapter = _make_mock_adapter_with_plan(plan_text)
        agent = _make_agent(adapter)

        with patch("agent_framework.agents.plan_and_solve.AgentLoop") as MockLoop:
            mock_loop = AsyncMock()
            mock_loop.run = lambda prompt: _async_iter([
                AgentEvent(type="done", step=1, data={"content": [{"type": "text", "text": "步骤完成"}]}),
            ])
            MockLoop.return_value = mock_loop

            events = await _collect_events(agent, "三步任务")

        types = [e.type for e in events]
        step_events = [e for e in events if e.type == "step"]
        done_events = [e for e in events if e.type == "done"]

        # 3 step events + 1 done event
        assert len(step_events) == 3
        assert len(done_events) == 1
        assert done_events[0].step == 3


class TestBuildStepPrompt:
    """_build_step_prompt 辅助方法测试。"""

    def test_no_prior_outputs(self) -> None:
        """无前序输出时不包含摘要。"""
        from agent_framework.orchestrator.planner import PlanItem
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)

        item = PlanItem(id="1", action="做某事", status="pending")
        prompt = agent._build_step_prompt("原始任务", item, [])

        assert "原始任务" in prompt
        assert "做某事" in prompt
        assert "前序步骤摘要" not in prompt

    def test_with_prior_outputs(self) -> None:
        """有前序输出时包含摘要。"""
        from agent_framework.orchestrator.planner import PlanItem
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)

        item = PlanItem(id="2", action="做另一事", status="pending")
        prompt = agent._build_step_prompt("原始任务", item, ["步骤一结果"])

        assert "前序步骤摘要" in prompt
        assert "步骤一结果" in prompt


class TestIsStepFailed:
    """_is_step_failed 规则检查详细测试。"""

    def test_empty_string_is_failed(self) -> None:
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)
        assert agent._is_step_failed("") is True

    def test_whitespace_only_is_failed(self) -> None:
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)
        assert agent._is_step_failed("  \n\t ") is True

    def test_sub_agent_error_is_failed(self) -> None:
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)
        assert agent._is_step_failed("[子代理错误] timeout") is True

    def test_normal_output_is_not_failed(self) -> None:
        adapter = _make_mock_adapter_with_text("")
        agent = _make_agent(adapter)
        assert agent._is_step_failed("任务完成，结果是...") is False


# ============================================================
# Helpers
# ============================================================


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
