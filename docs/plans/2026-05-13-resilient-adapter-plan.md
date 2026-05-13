# Resilient Adapter 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 retry.py 中已实现的 retry_with_backoff 和 CircuitBreaker 通过包装器模式集成到 Provider 调用链中。

**Architecture:** 创建 ResilientLLMAdapter 包装类（实现 ILLMAdapter），内部组合 provider + retry + breaker。创建 create_adapter() 工厂函数简化使用。不改动任何现有 Provider 代码。

**Tech Stack:** Python 3.11+, asyncio, pytest, unittest.mock

---

## Task 1: 添加 CircuitOpenError 异常

**Files:**
- Modify: `backend/app/core/llm/base.py:73` (在 LLMAdapterError 之后)
- Modify: `backend/app/core/llm/__init__.py`

**Step 1: 写失败测试**

创建 `backend/tests/test_resilient.py`:

```python
"""ResilientLLMAdapter 测试。"""

import pytest

from app.core.llm.base import (
    CircuitOpenError,
    ILLMAdapter,
    LLMAdapterError,
)
from app.core.llm.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
)
from app.core.llm.types import CompletionConfig, CompletionResult


def test_circuit_open_error_is_llm_adapter_error():
    """CircuitOpenError 应该是 LLMAdapterError 的子类。"""
    err = CircuitOpenError(provider="deepseek")
    assert isinstance(err, LLMAdapterError)
    assert err.retryable is False
    assert err.provider == "deepseek"
```

**Step 2: 运行测试验证失败**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py::test_circuit_open_error_is_llm_adapter_error -v`
Expected: FAIL — `ImportError: cannot import name 'CircuitOpenError'`

**Step 3: 在 base.py 中添加 CircuitOpenError**

在 `backend/app/core/llm/base.py` 的 `InvalidRequestError` 类之后（第 144 行后）添加：

```python
class CircuitOpenError(LLMAdapterError):
    """断路器打开，拒绝请求。"""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        *,
        provider: str = "",
    ) -> None:
        super().__init__(
            message,
            provider=provider,
            status_code=503,
            retryable=False,
        )
```

**Step 4: 在 __init__.py 中导出**

在 `backend/app/core/llm/__init__.py` 的 import 块中添加 `CircuitOpenError`，在 `__all__` 列表中添加 `"CircuitOpenError"`。

**Step 5: 运行测试验证通过**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py::test_circuit_open_error_is_llm_adapter_error -v`
Expected: PASS

**Step 6: 提交**

```bash
git add backend/app/core/llm/base.py backend/app/core/llm/__init__.py backend/tests/test_resilient.py
git commit -m "feat: add CircuitOpenError exception"
```

---

## Task 2: 实现 ResilientLLMAdapter.complete()

**Files:**
- Create: `backend/app/core/llm/resilient.py`
- Modify: `backend/tests/test_resilient.py`

**Step 1: 写失败测试**

在 `backend/tests/test_resilient.py` 中追加：

```python
from unittest.mock import AsyncMock, MagicMock


def _make_mock_provider() -> AsyncMock:
    """创建一个 mock provider，实现 ILLMAdapter 接口。"""
    provider = AsyncMock(spec=ILLMAdapter)
    provider.get_provider_info.return_value = MagicMock(
        provider="mock",
        model="mock-model",
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
        content=[],
        model="mock-model",
        stop_reason="end_turn",
        usage=UsageStats(input_tokens=0, output_tokens=0),
    )


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

    # max_retries=2 意味着最多调用 3 次（初始 + 2 次重试）
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
    # 手动触发熔断
    breaker.record_failure()

    adapter = ResilientLLMAdapter(provider=provider, breaker=breaker)

    with pytest.raises(CircuitOpenError):
        await adapter.complete(mock_config)

    provider.complete.assert_not_called()
```

**Step 2: 运行测试验证失败**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py -v`
Expected: FAIL — `cannot import name 'ResilientLLMAdapter'`

**Step 3: 实现 ResilientLLMAdapter**

创建 `backend/app/core/llm/resilient.py`:

```python
"""Resilient LLM Adapter — 包装 Provider 提供 retry + circuit breaker。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from .base import CircuitOpenError, ILLMAdapter, LLMAdapterError
from .retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    retry_with_backoff,
)
from .types import CompletionConfig, CompletionResult, ProviderInfo, StreamEvent

logger = logging.getLogger(__name__)


class ResilientLLMAdapter(ILLMAdapter):
    """组合 retry + circuit breaker 的 LLM Adapter 包装器。"""

    def __init__(
        self,
        provider: ILLMAdapter,
        retry_config: RetryConfig | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._provider = provider
        self._retry_config = retry_config or RetryConfig()
        self._breaker = breaker or CircuitBreaker(
            name=provider.get_provider_info().provider,
            config=CircuitBreakerConfig(),
        )

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        if not self._breaker.allow_request():
            info = self._provider.get_provider_info()
            raise CircuitOpenError(provider=info.provider)

        try:
            result = await retry_with_backoff(
                fn=lambda: self._provider.complete(config),
                config=self._retry_config,
            )
            self._breaker.record_success()
            return result
        except LLMAdapterError:
            self._breaker.record_failure()
            raise

    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]:
        if not self._breaker.allow_request():
            info = self._provider.get_provider_info()
            raise CircuitOpenError(provider=info.provider)

        try:
            stream = await retry_with_backoff(
                fn=lambda: self._provider.stream(config),
                config=self._retry_config,
            )
            self._breaker.record_success()
            return stream
        except LLMAdapterError:
            self._breaker.record_failure()
            raise

    def get_provider_info(self) -> ProviderInfo:
        return self._provider.get_provider_info()

    async def health_check(self) -> bool:
        try:
            ok = await self._provider.health_check()
            if ok:
                self._breaker.record_success()
            else:
                self._breaker.record_failure()
            return ok
        except Exception:
            self._breaker.record_failure()
            raise
```

**Step 4: 运行测试验证通过**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py -v`
Expected: 全部 PASS

**Step 5: 提交**

```bash
git add backend/app/core/llm/resilient.py backend/tests/test_resilient.py
git commit -m "feat: implement ResilientLLMAdapter with retry and circuit breaker"
```

---

## Task 3: 实现 create_adapter() 工厂函数

**Files:**
- Modify: `backend/app/core/llm/resilient.py`
- Modify: `backend/tests/test_resilient.py`

**Step 1: 写失败测试**

在 `backend/tests/test_resilient.py` 中追加：

```python
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
    assert info.provider == "deepseek"


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
    assert info.provider == "openai"


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
    assert info.provider == "anthropic"


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
    # 不报错就算成功
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
```

**Step 2: 运行测试验证失败**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py::test_create_adapter_deepseek -v`
Expected: FAIL — `cannot import name 'create_adapter'`

**Step 3: 在 resilient.py 中添加 create_adapter()**

在 `backend/app/core/llm/resilient.py` 底部追加：

```python
_PROVIDER_MAP: dict[str, str] = {
    "deepseek": "app.core.llm.providers.deepseek_provider.DeepSeekProvider",
    "openai": "app.core.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "app.core.llm.providers.anthropic_provider.AnthropicProvider",
}


def _import_provider_class(class_path: str) -> type:
    """动态导入 Provider 类。"""
    module_path, class_name = class_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_adapter(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
    retry_config: RetryConfig | None = None,
    breaker_config: CircuitBreakerConfig | None = None,
) -> ResilientLLMAdapter:
    """创建带 retry + circuit breaker 保护的 LLM Adapter。

    Args:
        provider: provider 名称 ("deepseek" | "openai" | "anthropic")
        api_key: API 密钥
        model: 模型名称
        base_url: 自定义 API 端点，None 则用默认值
        retry_config: 重试配置，None 用默认值
        breaker_config: 断路器配置，None 用默认值

    Returns:
        ResilientLLMAdapter 实例

    Raises:
        ValueError: 未知的 provider 名称
    """
    if provider not in _PROVIDER_MAP:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            f"Supported: {', '.join(_PROVIDER_MAP.keys())}"
        )

    cls = _import_provider_class(_PROVIDER_MAP[provider])

    kwargs: dict[str, Any] = {"api_key": api_key, "default_model": model}
    if base_url is not None:
        kwargs["base_url"] = base_url

    provider_instance: ILLMAdapter = cls(**kwargs)

    r_cfg = retry_config or RetryConfig()
    b_cfg = breaker_config or CircuitBreakerConfig()
    breaker = CircuitBreaker(name=provider, config=b_cfg)

    return ResilientLLMAdapter(
        provider=provider_instance,
        retry_config=r_cfg,
        breaker=breaker,
    )
```

**Step 4: 运行测试验证通过**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py -v`
Expected: 全部 PASS

**Step 5: 提交**

```bash
git add backend/app/core/llm/resilient.py backend/tests/test_resilient.py
git commit -m "feat: add create_adapter factory function with provider registry"
```

---

## Task 4: 更新 __init__.py 导出

**Files:**
- Modify: `backend/app/core/llm/__init__.py`

**Step 1: 更新导出**

在 `backend/app/core/llm/__init__.py` 中添加：

```python
from .resilient import ResilientLLMAdapter, create_adapter
```

在 `__all__` 中添加：

```python
"ResilientLLMAdapter",
"create_adapter",
```

**Step 2: 验证导入正常**

Run: `cd /Users/huhu/project/agent_framework/backend && python -c "from app.core.llm import ResilientLLMAdapter, create_adapter, CircuitOpenError; print('OK')"`
Expected: 输出 `OK`

**Step 3: 运行全部测试**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py -v`
Expected: 全部 PASS

**Step 4: 提交**

```bash
git add backend/app/core/llm/__init__.py
git commit -m "feat: export ResilientLLMAdapter and create_adapter from package"
```

---

## Task 5: 补充 stream() 和 health_check() 测试

**Files:**
- Modify: `backend/tests/test_resilient.py`

**Step 1: 写 stream 测试**

在 `backend/tests/test_resilient.py` 中追加：

```python
@pytest.mark.asyncio
async def test_stream_success(mock_config):
    """流式调用透传到 provider。"""
    from app.core.llm.resilient import ResilientLLMAdapter

    async def fake_stream(config):
        yield StreamEvent(event_type=StreamEventType.CONTENT_START, data={})

    provider = _make_mock_provider()
    provider.stream.return_value = fake_stream(mock_config)

    adapter = ResilientLLMAdapter(provider=provider)
    stream = await adapter.stream(mock_config)

    events = [e async for e in stream]
    assert len(events) == 1
    assert events[0].event_type == StreamEventType.CONTENT_START


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

    # 连续 2 次失败触发熔断
    assert breaker.state.value == "open"
```

**Step 2: 运行全部测试**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py -v`
Expected: 全部 PASS

**Step 3: 提交**

```bash
git add backend/tests/test_resilient.py
git commit -m "test: add stream and health_check tests for ResilientLLMAdapter"
```

---

## Task 6: 补充 pyproject.toml 测试依赖

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: 添加测试依赖**

在 `backend/pyproject.toml` 中添加 `[project.optional-dependencies]` 段：

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```

**Step 2: 验证安装**

Run: `cd /Users/huhu/project/agent_framework/backend && pip install -e ".[test]" 2>&1 | tail -5`

**Step 3: 运行全部测试确认**

Run: `cd /Users/huhu/project/agent_framework/backend && python -m pytest tests/test_resilient.py -v`
Expected: 全部 PASS

**Step 4: 提交**

```bash
git add backend/pyproject.toml
git commit -m "chore: add pytest and pytest-asyncio as test dependencies"
```
