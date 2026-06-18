"""Token 估算模块测试。"""

from unittest.mock import MagicMock

import pytest

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    AssistantMessage,
    CompletionConfig,
    ProviderInfo,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)
from agent_framework.tools.context.token_counter import (
    estimate_tokens,
    estimate_with_usage,
    get_effective_window,
)


# ============================================================
# estimate_tokens
# ============================================================


def test_estimate_tokens_empty_messages():
    """空消息列表返回 0。"""
    assert estimate_tokens([]) == 0


def test_estimate_tokens_with_system_message():
    """SystemMessage: len(content) * (1.33 / 4)。"""
    content = "a" * 100  # 100 chars
    messages: list = [SystemMessage(content=content)]

    expected = int(100 * 1.33 / 4)  # 33
    assert estimate_tokens(messages) == expected


def test_estimate_tokens_with_user_message():
    """UserMessage: 累加所有 TextBlock 的 len(text)。"""
    messages: list = [
        UserMessage(
            content=[
                TextBlock(text="hello world"),  # 11 chars
                TextBlock(text="second block"),  # 12 chars
            ]
        ),
        SystemMessage(content="system prompt"),  # 13 chars
    ]
    # total_chars = 11 + 12 + 13 = 36
    expected = int(36 * 1.33 / 4)  # 11
    assert estimate_tokens(messages) == expected


def test_estimate_tokens_with_tool_message():
    """ToolMessage: len(content)。"""
    messages: list = [
        ToolMessage(tool_call_id="call_1", content="tool result data here"),
    ]
    total_chars = len("tool result data here")  # 21
    expected = int(total_chars * 1.33 / 4)
    assert estimate_tokens(messages) == expected


def test_estimate_tokens_with_tool_use_block():
    """ToolUseBlock: len(str(input))。"""
    tool_input = {"query": "test", "limit": 10}
    messages: list = [
        AssistantMessage(
            content=[
                TextBlock(text="I will search"),
                ToolUseBlock(id="id_1", name="search", input=tool_input),
            ]
        ),
    ]
    total_chars = len("I will search") + len(str(tool_input))
    expected = int(total_chars * 1.33 / 4)
    assert estimate_tokens(messages) == expected


def test_estimate_tokens_with_tool_result_block():
    """ToolResultBlock: len(content)。"""
    messages: list = [
        UserMessage(
            content=[
                ToolResultBlock(tool_use_id="id_1", content="result payload"),
            ]
        ),
    ]
    total_chars = len("result payload")
    expected = int(total_chars * 1.33 / 4)
    assert estimate_tokens(messages) == expected


# ============================================================
# estimate_with_usage
# ============================================================


def test_estimate_with_usage():
    """混合估算: last_usage.input_tokens + estimate_tokens(new_messages)。"""
    new_messages = [
        SystemMessage(content="a" * 120),
    ]
    last_usage = UsageStats(input_tokens=1000)

    result = estimate_with_usage(new_messages, last_usage)
    assert result == 1000 + estimate_tokens(new_messages)


# ============================================================
# get_effective_window
# ============================================================


def test_get_effective_window_config_override():
    """Priority 1: config.max_context_tokens 优先。"""
    adapter = MagicMock(spec=ILLMAdapter)
    adapter.get_max_context_tokens = MagicMock(return_value=8000)
    adapter.get_provider_info = MagicMock(
        return_value=ProviderInfo(
            name="test",
            base_url="http://test",
            default_model="test-model",
            max_context_tokens=128000,
        )
    )

    config = CompletionConfig(
        model="test-model",
        messages=[],
        max_context_tokens=4000,
    )

    assert get_effective_window(adapter, config) == 4000


def test_get_effective_window_adapter_override():
    """Priority 2: adapter.get_max_context_tokens() 当 config 为 None 时生效。"""
    adapter = MagicMock(spec=ILLMAdapter)
    adapter.get_max_context_tokens = MagicMock(return_value=16000)
    adapter.get_provider_info = MagicMock(
        return_value=ProviderInfo(
            name="test",
            base_url="http://test",
            default_model="test-model",
            max_context_tokens=128000,
        )
    )

    config = CompletionConfig(
        model="test-model",
        messages=[],
        max_context_tokens=None,
    )

    assert get_effective_window(adapter, config) == 16000


def test_get_effective_window_provider_default():
    """Priority 3: provider info 的 max_context_tokens 作为兜底。"""
    adapter = MagicMock(spec=ILLMAdapter)
    # 没有 get_max_context_tokens 方法 → getattr 返回 MagicMock（非 None 但不可调用为期望行为）
    # 实际上 spec=ILLMAdapter 不包含 get_max_context_tokens，所以 MagicMock 会自动创建
    # 但它的返回值不是 None，我们需要模拟一个没有该方法的 adapter
    del adapter.get_max_context_tokens  # 删除该方法模拟普通 adapter

    adapter.get_provider_info = MagicMock(
        return_value=ProviderInfo(
            name="test",
            base_url="http://test",
            default_model="test-model",
            max_context_tokens=200000,
        )
    )

    config = CompletionConfig(
        model="test-model",
        messages=[],
        max_context_tokens=None,
    )

    assert get_effective_window(adapter, config) == 200000


def test_get_effective_window_adapter_returns_none():
    """当 adapter.get_max_context_tokens() 返回 None 时，回退到 provider。"""
    adapter = MagicMock(spec=ILLMAdapter)
    adapter.get_max_context_tokens = MagicMock(return_value=None)
    adapter.get_provider_info = MagicMock(
        return_value=ProviderInfo(
            name="test",
            base_url="http://test",
            default_model="test-model",
            max_context_tokens=128000,
        )
    )

    config = CompletionConfig(
        model="test-model",
        messages=[],
        max_context_tokens=None,
    )

    assert get_effective_window(adapter, config) == 128000
