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
