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
            name=provider.get_provider_info().name,
            config=CircuitBreakerConfig(),
        )

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        if not self._breaker.allow_request():
            info = self._provider.get_provider_info()
            raise CircuitOpenError(provider=info.name)

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
            raise CircuitOpenError(provider=info.name)

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


# ============================================================
# 工厂函数
# ============================================================


_PROVIDER_MAP: dict[str, str] = {
    "deepseek": "agent_framework.llm.providers.deepseek_provider.DeepSeekProvider",
    "openai": "agent_framework.llm.providers.openai_provider.OpenAIProvider",
    "anthropic": "agent_framework.llm.providers.anthropic_provider.AnthropicProvider",
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
    """工厂函数：按 provider 名称创建 ResilientLLMAdapter。"""
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
