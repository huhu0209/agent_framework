"""重试策略与 Circuit Breaker。

重试策略：
- 429 (rate limit) → 读取 retry-after header → 指数退避 + jitter
- 5xx → 指数退避，最多 3 次
- 400 (schema error) → 不重试
- timeout → 区分 connect/read/total

Circuit Breaker：
- 连续 N 次失败 → unhealthy
- 冷却期后 half-open 探测
- 探测成功 → 恢复

所有状态存内存，不需要 Redis。
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from .base import (
    InvalidRequestError,
    LLMAdapterError,
    RateLimitError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


# ============================================================
# 重试策略
# ============================================================


@dataclass(frozen=True)
class RetryConfig:
    """重试配置。"""

    max_retries: int = 3
    base_delay: float = 1.0  # 秒
    max_delay: float = 60.0  # 秒
    jitter_factor: float = 0.1  # 10% 随机抖动


def _calculate_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: float | None = None,
) -> float:
    """计算第 N 次重试的等待时间（指数退避 + jitter）。

    Args:
        attempt: 当前重试次数（从 0 开始）
        config: 重试配置
        retry_after: 服务端建议的等待时间（429 header）

    Returns:
        等待秒数
    """
    # 如果服务端给了 retry-after，优先使用
    if retry_after is not None:
        return min(retry_after, config.max_delay)

    # 指数退避: base_delay * 2^attempt
    delay = config.base_delay * (2 ** attempt)
    delay = min(delay, config.max_delay)

    # 加 jitter 避免雷群效应
    jitter = delay * config.jitter_factor * random.random()
    return delay + jitter


def should_retry(error: LLMAdapterError, attempt: int, config: RetryConfig) -> bool:
    """判断是否应该重试。

    规则：
    - 不重试: 400 (InvalidRequestError)
    - 可重试: 429 (RateLimitError), 5xx (ServiceUnavailableError), timeout
    - 超过 max_retries 不重试
    """
    if attempt >= config.max_retries:
        return False

    if isinstance(error, InvalidRequestError):
        return False

    return error.retryable


async def retry_with_backoff(
    fn: Callable[[], Coroutine[Any, Any, Any]],
    config: RetryConfig | None = None,
    on_retry: Callable[[int, LLMAdapterError, float], None] | None = None,
) -> Any:
    """带指数退避的重试包装器。

    Args:
        fn: 要执行的异步函数
        config: 重试配置
        on_retry: 重试回调（attempt, error, delay）

    Returns:
        fn 的返回值

    Raises:
        最后一次的 LLMAdapterError
    """
    if config is None:
        config = RetryConfig()

    last_error: LLMAdapterError | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await fn()
        except LLMAdapterError as exc:
            last_error = exc

            if not should_retry(exc, attempt, config):
                raise

            retry_after = exc.retry_after if isinstance(exc, RateLimitError) else None
            delay = _calculate_delay(attempt, config, retry_after)

            if on_retry:
                on_retry(attempt, exc, delay)
            else:
                logger.warning(
                    "Retry %d/%d after %.1fs: %s",
                    attempt + 1,
                    config.max_retries,
                    delay,
                    str(exc)[:100],
                )

            await asyncio.sleep(delay)

    # 理论上不会到达，但类型安全
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")


# ============================================================
# Circuit Breaker
# ============================================================


class CircuitState(str, Enum):
    """断路器状态。"""

    CLOSED = "closed"       # 正常
    OPEN = "open"           # 熔断（拒绝请求）
    HALF_OPEN = "half_open" # 探测（允许一个请求测试）


@dataclass
class CircuitBreakerConfig:
    """断路器配置。"""

    failure_threshold: int = 5      # 连续失败多少次触发熔断
    recovery_timeout: float = 60.0  # 熔断后等待多少秒开始探测
    success_threshold: int = 2      # 探测期连续成功多少次恢复


@dataclass
class CircuitBreaker:
    """Provider 级别的断路器。

    状态转换：
    CLOSED → 连续 N 次失败 → OPEN
    OPEN → 等待 recovery_timeout → HALF_OPEN
    HALF_OPEN → 成功 M 次 → CLOSED
    HALF_OPEN → 任何失败 → OPEN

    线程安全：适用于单进程 async 场景，不适用于多进程。
    """

    name: str = "default"
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _success_count: int = 0
    _last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """当前状态（自动检查是否该进入 HALF_OPEN）。"""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self.config.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
        return self._state

    def allow_request(self) -> bool:
        """是否允许发起请求。"""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True  # 允许探测请求
        return False  # OPEN 状态拒绝

    def record_success(self) -> None:
        """记录成功。"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                logger.info("Circuit breaker '%s' recovered: CLOSED", self.name)
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """记录失败。"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker '%s' probe failed: back to OPEN", self.name)
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif self._failure_count >= self.config.failure_threshold:
            logger.warning(
                "Circuit breaker '%s' tripped: %d consecutive failures → OPEN",
                self.name,
                self._failure_count,
            )
            self._state = CircuitState.OPEN

    def get_stats(self) -> dict[str, Any]:
        """返回当前状态统计（用于监控）。"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
        }

    def reset(self) -> None:
        """手动重置断路器。"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
