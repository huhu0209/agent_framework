"""ReflectionAgent + ReflectionVerdict 测试。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.reflection import ReflectionAgent, ReflectionVerdict
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


# ============================================================
# 测试辅助
# ============================================================


def _make_verdict_json(
    satisfied: bool,
    scores: dict | None = None,
    critique: str = "",
) -> str:
    """构造 JSON 格式的 verdict 字符串。"""
    return json.dumps({
        "satisfied": satisfied,
        "scores": scores or {},
        "critique": critique,
    })


def _text_result(text: str) -> CompletionResult:
    """构造文本完成结果。"""
    return CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(),
    )


def _make_mock_adapter(side_effects: list | None = None) -> AsyncMock:
    """创建有预设 side_effect 序列的 mock adapter。"""
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    if side_effects is not None:
        adapter.complete.side_effect = side_effects
    return adapter


def _make_agent(adapter: AsyncMock, **kwargs) -> ReflectionAgent:
    """创建 ReflectionAgent 实例。"""
    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    return ReflectionAgent(
        adapter,
        model="mock",
        router=router,
        ctx=ctx,
        **kwargs,
    )


async def _collect_events(
    agent: ReflectionAgent, message: str,
) -> list[AgentEvent]:
    """收集 agent.run() 产出的所有事件。"""
    return [event async for event in agent.run(message)]


# ============================================================
# TestReflectionVerdict
# ============================================================


class TestReflectionVerdict:
    """ReflectionVerdict 解析测试。"""

    def test_parse_valid_json(self) -> None:
        """合法 JSON 正常解析。"""
        text = _make_verdict_json(
            True,
            {"correctness": 5, "completeness": 4, "clarity": 5},
            "很好",
        )
        verdict = ReflectionVerdict.from_llm_response(text)
        assert verdict.satisfied is True
        assert verdict.scores == {"correctness": 5, "completeness": 4, "clarity": 5}
        assert verdict.critique == "很好"

    def test_parse_invalid_json(self) -> None:
        """非法 JSON 返回默认值。"""
        verdict = ReflectionVerdict.from_llm_response("这不是 JSON")
        assert verdict.satisfied is False
        assert verdict.scores == {}
        assert "评估失败" in verdict.critique

    def test_parse_embedded_json(self) -> None:
        """从混合文本中提取 JSON。"""
        text = (
            "评估结果如下：\n"
            '{"satisfied": false, "scores": {"correctness": 3}, '
            '"critique": "需要改进"}\n'
            "以上是评估。"
        )
        verdict = ReflectionVerdict.from_llm_response(text)
        assert verdict.satisfied is False
        assert verdict.scores == {"correctness": 3}
        assert verdict.critique == "需要改进"

    def test_parse_missing_fields(self) -> None:
        """缺少字段使用默认值。"""
        verdict = ReflectionVerdict.from_llm_response('{"satisfied": true}')
        assert verdict.satisfied is True
        assert verdict.scores == {}
        assert verdict.critique == ""

    def test_parse_satisfied_coercion(self) -> None:
        """satisfied 字段强制转为 bool。"""
        verdict = ReflectionVerdict.from_llm_response(
            '{"satisfied": 1, "scores": {}, "critique": ""}'
        )
        assert verdict.satisfied is True


# ============================================================
# TestReflectionAgent
# ============================================================


class TestReflectionAgent:
    """ReflectionAgent 行为测试。"""

    def test_inherits_agent(self) -> None:
        """REFL-01: ReflectionAgent 继承 Agent。"""
        assert issubclass(ReflectionAgent, Agent)

    @pytest.mark.asyncio
    async def test_first_round_satisfied(self) -> None:
        """首轮评估即满意，只执行 1 轮。"""
        adapter = _make_mock_adapter()

        # AgentLoop.run() 会调用 adapter.complete() 一次（返回文本结果）
        # 然后 _reflect() 也会调用 adapter.complete() 一次（返回评估 verdict）
        # 构造 side_effect: [执行结果, 评估结果]
        adapter.complete.side_effect = [
            _text_result("这是执行结果"),  # AgentLoop 执行
            _text_result(_make_verdict_json(True, {"correctness": 5})),  # 评估：满意
        ]

        agent = _make_agent(adapter)
        events = await _collect_events(agent, "做一件事")

        # 应该只有 done 事件（首轮即满意）
        done_events = [e for e in events if e.type == "done"]
        assert len(done_events) == 1
        assert done_events[0].data["verdict"]["satisfied"] is True
        # 没有 step 类型的改进事件
        improvement_events = [
            e for e in events
            if e.type == "step" and "改进" in e.data.get("text", "")
        ]
        assert len(improvement_events) == 0

    @pytest.mark.asyncio
    async def test_max_improvement_rounds(self) -> None:
        """REFL-03: 改进轮次硬上限 1 次（max_improvement_rounds=1）。"""
        adapter = _make_mock_adapter()

        # 最多 2 轮（1 执行 + 1 改进），每轮 2 次 complete（执行 + 评估）
        adapter.complete.side_effect = [
            _text_result("第一轮输出"),  # 第 1 轮执行
            _text_result(_make_verdict_json(False, critique="不好")),  # 第 1 轮评估
            _text_result("第二轮改进输出"),  # 第 2 轮执行
            _text_result(_make_verdict_json(False, critique="仍不好")),  # 第 2 轮评估
        ]

        agent = _make_agent(adapter, max_improvement_rounds=1)
        events = await _collect_events(agent, "做一件事")

        # 最终 done 事件包含 max_rounds_reached=True
        done_events = [e for e in events if e.type == "done"]
        assert len(done_events) == 1
        assert done_events[0].data["verdict"]["max_rounds_reached"] is True
        assert done_events[0].data["verdict"]["satisfied"] is False

    @pytest.mark.asyncio
    async def test_critique_injection(self) -> None:
        """REFL-04: critique 注入到第二轮 prompt。"""
        adapter = _make_mock_adapter()
        critique_text = "请增加更多细节"

        adapter.complete.side_effect = [
            _text_result("第一轮输出"),  # 第 1 轮执行
            _text_result(_make_verdict_json(False, critique=critique_text)),  # 第 1 轮评估
            _text_result("第二轮改进输出"),  # 第 2 轮执行
            _text_result(_make_verdict_json(True)),  # 第 2 轮评估：满意
        ]

        agent = _make_agent(adapter, max_improvement_rounds=2)
        events = await _collect_events(agent, "做一件事")

        # 验证改进事件中包含 critique
        improvement_events = [
            e for e in events
            if e.type == "step" and "改进" in e.data.get("text", "")
        ]
        assert len(improvement_events) == 1
        assert improvement_events[0].data["verdict"]["critique"] == critique_text

        # 验证第二轮 prompt 包含 [评估反馈]（检查第二次调用 AgentLoop 时的消息）
        # adapter.complete 被调用 4 次，第 3 次是第二轮执行
        # 检查第 3 次调用的 config.messages 中是否包含 critique
        calls = adapter.complete.call_args_list
        assert len(calls) == 4
        third_call_config: CompletionConfig = calls[2].args[0]
        messages_text = str(third_call_config.messages)
        assert "[评估反馈]" in messages_text
        assert critique_text in messages_text

        # 最终 done 满意
        done_events = [e for e in events if e.type == "done"]
        assert done_events[-1].data["verdict"]["satisfied"] is True
