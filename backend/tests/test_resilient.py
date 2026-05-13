"""ResilientLLMAdapter 测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.llm.base import (
    CircuitOpenError,
    ILLMAdapter,
    InvalidRequestError,
    LLMAdapterError,
    ServiceUnavailableError,
)
from app.core.llm.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
)
from app.core.llm.resilient import ResilientLLMAdapter
from app.core.llm.types import (
    CompletionConfig,
    CompletionResult,
    ProviderInfo,
    StreamEvent,
    StreamEventType,
    UsageStats,
)


def _make_mock_provider() -> AsyncMock:
    """创建一个 mock provider，实现 ILLMAdapter 接口。"""
    provider = AsyncMock(spec=ILLMAdapter)
    provider.get_provider_info.return_value = ProviderInfo(
        name="mock",
        base_url="https://mock.test",
        default_model="mock-model",
    )
    return provider


@pytest.fixture
def mock_config() -> CompletionConfig:
    """创建一个最小的 CompletionConfig。"""
    return CompletionConfig(
        model="mock-model",
        messages=[],
    )


@pytest.fixture
def mock_result() -> CompletionResult:
    """创建一个 mock CompletionResult。"""
    return CompletionResult(
        id="test-id",
        content=[],
        model="mock-model",
        stop_reason="end_turn",
        usage=UsageStats(input_tokens=0, output_tokens=0),
    )


# ---- Task 1 测试 ----


def test_circuit_open_error_is_llm_adapter_error():
    """CircuitOpenError 应该是 LLMAdapterError 的子类。"""
    err = CircuitOpenError(provider="deepseek")
    assert isinstance(err, LLMAdapterError)
    assert err.retryable is False
    assert err.provider == "deepseek"


# ---- Task 2 测试 ----


@pytest.mark.asyncio
async def test_complete_success(mock_config, mock_result):
    """正常调用直接透传到 provider。"""
    provider = _make_mock_provider()
    provider.complete.return_value = mock_result

    from app.core.llm.resilient import ResilientLLMAdapter

    adapter = ResilientLLMAdapter(provider=provider)
    result = await adapter.complete(mock_config)

    assert result == mock_result
    provider.complete.assert_called_once_with(mock_config)


@pytest.mark.asyncio
async def test_complete_retries_on_retryable_error(mock_config, mock_result):
    """可重试错误触发重试，最终成功。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    provider.complete.side_effect = [
        ServiceUnavailableError(provider="mock"),
        mock_result,  # 第二次成功
    ]

    adapter = ResilientLLMAdapter(
        provider=provider,
        retry_config=RetryConfig(max_retries=3, base_delay=0.01),
    )
    result = await adapter.complete(mock_config)

    assert result == mock_result
    assert provider.complete.call_count == 2


@pytest.mark.asyncio
async def test_complete_no_retry_on_invalid_request(mock_config):
    """不可重试错误直接抛出，不重试。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    provider.complete.side_effect = InvalidRequestError(provider="mock")

    adapter = ResilientLLMAdapter(
        provider=provider,
        retry_config=RetryConfig(max_retries=3, base_delay=0.01),
    )

    with pytest.raises(InvalidRequestError):
        await adapter.complete(mock_config)

    assert provider.complete.call_count == 1


@pytest.mark.asyncio
async def test_complete_exhausts_retries(mock_config):
    """重试耗尽后抛出最后一次错误。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    provider.complete.side_effect = ServiceUnavailableError(provider="mock")

    adapter = ResilientLLMAdapter(
        provider=provider,
        retry_config=RetryConfig(max_retries=2, base_delay=0.01),
    )

    with pytest.raises(ServiceUnavailableError):
        await adapter.complete(mock_config)

    assert provider.complete.call_count == 3


@pytest.mark.asyncio
async def test_complete_blocked_by_open_breaker(mock_config):
    """断路器打开时抛出 CircuitOpenError。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    breaker = CircuitBreaker(
        name="test",
        config=CircuitBreakerConfig(failure_threshold=1),
    )
    breaker.record_failure()

    adapter = ResilientLLMAdapter(provider=provider, breaker=breaker)

    with pytest.raises(CircuitOpenError):
        await adapter.complete(mock_config)

    provider.complete.assert_not_called()


# ---- Task 3 测试 ----


@pytest.mark.asyncio
async def test_create_adapter_deepseek():
    """工厂函数创建 DeepSeek provider 的 resilient adapter。"""
    from app.core.llm.resilient import create_adapter

    adapter = create_adapter(
        provider="deepseek",
        api_key="test-key",
        model="deepseek-chat",
    )
    assert isinstance(adapter, ResilientLLMAdapter)
    info = adapter.get_provider_info()
    assert info.name == "deepseek"


@pytest.mark.asyncio
async def test_create_adapter_openai():
    """工厂函数创建 OpenAI provider。"""
    from app.core.llm.resilient import create_adapter

    adapter = create_adapter(
        provider="openai",
        api_key="test-key",
        model="gpt-4o",
    )
    assert isinstance(adapter, ResilientLLMAdapter)
    info = adapter.get_provider_info()
    assert info.name == "openai"


@pytest.mark.asyncio
async def test_create_adapter_anthropic():
    """工厂函数创建 Anthropic provider。"""
    from app.core.llm.resilient import create_adapter

    adapter = create_adapter(
        provider="anthropic",
        api_key="test-key",
        model="claude-sonnet-4-5-20250514",
    )
    assert isinstance(adapter, ResilientLLMAdapter)
    info = adapter.get_provider_info()
    assert info.name == "anthropic"


@pytest.mark.asyncio
async def test_create_adapter_custom_base_url():
    """工厂函数支持自定义 base_url。"""
    from app.core.llm.resilient import create_adapter

    adapter = create_adapter(
        provider="openai",
        api_key="test-key",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    assert isinstance(adapter, ResilientLLMAdapter)


def test_create_adapter_unknown_provider():
    """未知 provider 抛出 ValueError。"""
    from app.core.llm.resilient import create_adapter

    with pytest.raises(ValueError, match="Unknown provider"):
        create_adapter(
            provider="unknown",
            api_key="test-key",
            model="test",
        )


# ---- Task 5 测试 ----


@pytest.mark.asyncio
async def test_stream_success(mock_config):
    """流式调用透传到 provider。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    async def fake_stream(config):
        yield StreamEvent(type=StreamEventType.TEXT_DELTA, data={})

    provider = _make_mock_provider()
    provider.stream.return_value = fake_stream(mock_config)

    adapter = ResilientLLMAdapter(provider=provider)
    stream = await adapter.stream(mock_config)

    events = [e async for e in stream]
    assert len(events) == 1
    assert events[0].type == StreamEventType.TEXT_DELTA


@pytest.mark.asyncio
async def test_stream_blocked_by_open_breaker(mock_config):
    """断路器打开时流式调用也抛 CircuitOpenError。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    breaker = CircuitBreaker(
        name="test",
        config=CircuitBreakerConfig(failure_threshold=1),
    )
    breaker.record_failure()

    adapter = ResilientLLMAdapter(provider=provider, breaker=breaker)

    with pytest.raises(CircuitOpenError):
        await adapter.stream(mock_config)

    provider.stream.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_records_success():
    """health_check 成功时 breaker 记录成功。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    provider.health_check.return_value = True
    breaker = CircuitBreaker(
        name="test",
        config=CircuitBreakerConfig(failure_threshold=5),
    )

    adapter = ResilientLLMAdapter(provider=provider, breaker=breaker)
    result = await adapter.health_check()

    assert result is True
    assert breaker.state.value == "closed"


@pytest.mark.asyncio
async def test_health_check_records_failure():
    """health_check 失败时 breaker 记录失败。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    provider = _make_mock_provider()
    provider.health_check.return_value = False
    breaker = CircuitBreaker(
        name="test",
        config=CircuitBreakerConfig(failure_threshold=2),
    )

    adapter = ResilientLLMAdapter(provider=provider, breaker=breaker)
    await adapter.health_check()
    await adapter.health_check()

    assert breaker.state.value == "open"
