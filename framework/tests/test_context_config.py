"""Context window config — max_context_tokens 三级优先级支持。"""

from unittest.mock import AsyncMock

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.resilient import ResilientLLMAdapter, create_adapter
from agent_framework.llm.types import CompletionConfig, ProviderInfo


def _make_mock_provider() -> AsyncMock:
    """创建一个 mock provider，实现 ILLMAdapter 接口。"""
    provider = AsyncMock(spec=ILLMAdapter)
    provider.get_provider_info.return_value = ProviderInfo(
        name="mock",
        base_url="https://mock.test",
        default_model="mock-model",
    )
    return provider


# ---- CompletionConfig 测试 ----


def test_completion_config_accepts_max_context_tokens():
    """CompletionConfig 接受并存储 max_context_tokens。"""
    config = CompletionConfig(
        model="mock-model",
        messages=[],
        max_context_tokens=64000,
    )
    assert config.max_context_tokens == 64000


def test_completion_config_default_is_none():
    """CompletionConfig 的 max_context_tokens 默认为 None。"""
    config = CompletionConfig(model="mock-model", messages=[])
    assert config.max_context_tokens is None


# ---- create_adapter 测试 ----


def test_create_adapter_passes_max_context_tokens():
    """工厂函数将 max_context_tokens 传递给 ResilientLLMAdapter。"""
    adapter = create_adapter(
        provider="deepseek",
        api_key="test-key",
        model="deepseek-chat",
        max_context_tokens=96000,
    )
    assert adapter.get_max_context_tokens() == 96000


def test_create_adapter_default_is_none():
    """工厂函数不传 max_context_tokens 时默认为 None。"""
    adapter = create_adapter(
        provider="deepseek",
        api_key="test-key",
        model="deepseek-chat",
    )
    assert adapter.get_max_context_tokens() is None


# ---- ResilientLLMAdapter 测试 ----


def test_resilient_adapter_get_max_context_tokens():
    """ResilientLLMAdapter 存储并返回 max_context_tokens。"""
    provider = _make_mock_provider()
    adapter = ResilientLLMAdapter(
        provider=provider,
        max_context_tokens=128000,
    )
    assert adapter.get_max_context_tokens() == 128000


def test_resilient_adapter_default_is_none():
    """ResilientLLMAdapter 不传 max_context_tokens 时默认为 None。"""
    provider = _make_mock_provider()
    adapter = ResilientLLMAdapter(provider=provider)
    assert adapter.get_max_context_tokens() is None
