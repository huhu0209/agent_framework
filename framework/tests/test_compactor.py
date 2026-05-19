"""上下文自动压缩模块测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    AssistantMessage,
    CompletionResult,
    ProviderInfo,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)
from agent_framework.tools.context.compactor import (
    CompactConfig,
    _generate_summary,
    _group_by_user_turns,
    _serialize_for_summary,
    compact,
    should_compact,
)


# ============================================================
# Helpers
# ============================================================


def _make_mock_adapter(summary_text="## 已完成工作\n测试摘要。"):
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock",
        base_url="https://mock",
        default_model="mock-model",
    )
    adapter.complete.return_value = CompletionResult(
        id="summary-id",
        model="mock-model",
        content=[TextBlock(text=summary_text)],
        usage=UsageStats(input_tokens=100, output_tokens=50),
    )
    return adapter


def _make_user_turn(text: str) -> list:
    """创建一个简单的用户轮次：UserMessage + AssistantMessage。"""
    return [
        UserMessage(content=[TextBlock(text=text)]),
        AssistantMessage(content=[TextBlock(text=f"Response to: {text}")]),
    ]


def _make_messages_with_turns(n_turns: int, system: str = "system prompt") -> list:
    """创建包含 n_turns 个用户轮次的消息列表。"""
    messages: list = [SystemMessage(content=system)]
    for i in range(n_turns):
        messages.extend(_make_user_turn(f"Turn {i}"))
    return messages


# ============================================================
# should_compact
# ============================================================


class TestShouldCompact:
    def test_below_threshold_returns_false(self):
        """低于阈值 → False。"""
        config = CompactConfig(trigger_pct=0.75)
        assert should_compact(estimated=50000, window=100000, config=config) is False

    def test_above_threshold_returns_true(self):
        """超过阈值 → True。"""
        config = CompactConfig(trigger_pct=0.75)
        assert should_compact(estimated=80000, window=100000, config=config) is True

    def test_near_overhead_limit_returns_true(self):
        """接近 overhead 限制（window - 8000）时 → True。"""
        config = CompactConfig(trigger_pct=0.95)
        # trigger_pct * 100000 = 95000, but window - 8000 = 92000
        # min(95000, 92000) = 92000
        assert should_compact(estimated=93000, window=100000, config=config) is True

    def test_small_window_overhead_dominates(self):
        """小窗口时 overhead 主导 → True。"""
        config = CompactConfig(trigger_pct=0.75)
        # 0.75 * 10000 = 7500, but window - 8000 = 2000
        # min(7500, 2000) = 2000
        assert should_compact(estimated=3000, window=10000, config=config) is True


# ============================================================
# _group_by_user_turns
# ============================================================


class TestGroupByUserTurns:
    def test_single_turn(self):
        """单轮对话：一组。"""
        messages = [
            SystemMessage(content="system"),
            UserMessage(content=[TextBlock(text="hello")]),
            AssistantMessage(content=[TextBlock(text="hi")]),
        ]
        system_prefix, groups = _group_by_user_turns(messages)

        assert len(system_prefix) == 1
        assert isinstance(system_prefix[0], SystemMessage)
        assert len(groups) == 1
        assert isinstance(groups[0][0], UserMessage)

    def test_multiple_turns(self):
        """多轮对话：每个 UserMessage 开始一个新组。"""
        messages = [
            SystemMessage(content="sys"),
            UserMessage(content=[TextBlock(text="q1")]),
            AssistantMessage(content=[TextBlock(text="a1")]),
            UserMessage(content=[TextBlock(text="q2")]),
            AssistantMessage(content=[TextBlock(text="a2")]),
            UserMessage(content=[TextBlock(text="q3")]),
            AssistantMessage(content=[TextBlock(text="a3")]),
        ]
        system_prefix, groups = _group_by_user_turns(messages)

        assert len(system_prefix) == 1
        assert len(groups) == 3
        # 每组 [User, Assistant]
        for g in groups:
            assert isinstance(g[0], UserMessage)

    def test_with_tool_messages(self):
        """ToolMessage 归属当前轮次。"""
        messages = [
            SystemMessage(content="sys"),
            UserMessage(content=[TextBlock(text="do thing")]),
            AssistantMessage(content=[ToolUseBlock(id="c1", name="tool", input={})]),
            ToolMessage(tool_call_id="c1", content="result"),
            AssistantMessage(content=[TextBlock(text="done")]),
        ]
        system_prefix, groups = _group_by_user_turns(messages)

        assert len(groups) == 1
        # 组内: User, Assistant(tool_use), ToolMessage, Assistant
        assert len(groups[0]) == 4
        assert isinstance(groups[0][2], ToolMessage)

    def test_empty_messages(self):
        """空消息列表。"""
        system_prefix, groups = _group_by_user_turns([])
        assert system_prefix == []
        assert groups == []


# ============================================================
# compact
# ============================================================


class TestCompact:
    @pytest.mark.asyncio
    async def test_below_keep_turns_no_compression(self):
        """轮次不足 keep_turns → 不压缩，返回原始消息。"""
        config = CompactConfig(keep_turns=20)
        adapter = _make_mock_adapter()
        messages = _make_messages_with_turns(5)

        result = await compact(messages, adapter, "mock-model", config, step=10)

        assert result is messages
        adapter.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_triggers_summarization(self):
        """轮次超过 keep_turns → 触发摘要压缩。"""
        config = CompactConfig(keep_turns=3)
        adapter = _make_mock_adapter()
        messages = _make_messages_with_turns(6)

        result = await compact(messages, adapter, "mock-model", config, step=42)

        adapter.complete.assert_called_once()
        # 结果包含: system + (summary merged with first recent UserMessage) + rest
        # normalize_messages 会将相邻同角色消息合并，所以 summary UserMessage
        # 会与第一个 recent UserMessage 合并
        # system(1) + merged_summary_user(1) + assistant(1) + user(1) + assistant(1) + user(1) + assistant(1) = 7
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], UserMessage)  # summary + first recent user merged

    @pytest.mark.asyncio
    async def test_preserves_recent_turns(self):
        """最近 keep_turns 轮的消息内容不变。"""
        config = CompactConfig(keep_turns=2)
        adapter = _make_mock_adapter()
        messages = _make_messages_with_turns(4)

        result = await compact(messages, adapter, "mock-model", config, step=1)

        # recent turns: Turn 2, Turn 3 (last 2 turns)
        # normalize_messages merges: summary UserMessage + Turn 2 UserMessage → combined
        # result = system(1) + merged_summary+Turn2_user(1) + Turn2_assistant(1) + Turn3_user(1) + Turn3_assistant(1) = 5
        assert len(result) == 5
        # The merged message contains both summary and Turn 2 text
        merged = result[1]
        assert isinstance(merged, UserMessage)
        all_text = " ".join(b.text for b in merged.content if isinstance(b, TextBlock))
        assert "Turn 2" in all_text
        # Turn 3 user is separate
        assert isinstance(result[3], UserMessage)
        assert "Turn 3" in result[3].content[0].text

    @pytest.mark.asyncio
    async def test_summary_uses_no_tools(self):
        """摘要调用不携带 tools，max_tokens 使用配置值。"""
        config = CompactConfig(keep_turns=1, max_summary_tokens=4000)
        adapter = _make_mock_adapter()
        messages = _make_messages_with_turns(3)

        await compact(messages, adapter, "mock-model", config, step=5)

        call_config = adapter.complete.call_args[0][0]
        assert call_config.tools == []
        assert call_config.max_tokens == 4000
        assert call_config.temperature == 0.3

    @pytest.mark.asyncio
    async def test_boundary_marker_contains_step_and_count(self):
        """边界标记包含 step 号和消息计数。"""
        config = CompactConfig(keep_turns=2)
        adapter = _make_mock_adapter()
        messages = _make_messages_with_turns(4)
        # 4 turns, keep 2 → old 2 turns = 4 messages (2 user + 2 assistant)

        result = await compact(messages, adapter, "mock-model", config, step=77)

        # summary is result[1] — a UserMessage
        summary_msg = result[1]
        assert isinstance(summary_msg, UserMessage)
        text = summary_msg.content[0].text
        assert "step 77" in text
        assert "4 条消息" in text


# ============================================================
# _serialize_for_summary
# ============================================================


class TestSerializeForSummary:
    def test_basic_serialization(self):
        """基本消息序列化格式正确。"""
        messages = [
            SystemMessage(content="system prompt"),
            UserMessage(content=[TextBlock(text="hello")]),
            AssistantMessage(content=[TextBlock(text="world")]),
            ToolMessage(tool_call_id="c1", content="tool output"),
        ]
        result = _serialize_for_summary(messages)

        assert "[System] system prompt" in result
        assert "[User] hello" in result
        assert "[Assistant] world" in result
        assert "[Tool:c1] tool output" in result

    def test_tool_message_truncated_at_500(self):
        """ToolMessage 内容超过 500 字符时截断。"""
        long_content = "x" * 600
        messages = [
            ToolMessage(tool_call_id="c1", content=long_content),
        ]
        result = _serialize_for_summary(messages)
        assert len(result.split("] ", 1)[1]) == 500
