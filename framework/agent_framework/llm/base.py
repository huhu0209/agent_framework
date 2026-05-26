"""LLM Adapter 抽象基类。

所有 provider 必须实现此接口。Adapter 只做"跟一家模型对话"这件事，
路由逻辑由 core/orchestrator/router.py 负责。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .types import CompletionConfig, CompletionResult, ProviderInfo, StreamEvent


class ILLMAdapter(ABC):
    """LLM Provider 适配器抽象接口。

    职责：
    1. 接收统一的 CompletionConfig
    2. 转换为目标 provider 的 HTTP 请求格式
    3. 发送请求并处理响应
    4. 将响应转换回统一的 CompletionResult

    不负责：路由、重试（由 retry.py 包装）、上下文管理
    """

    @abstractmethod
    async def complete(self, config: CompletionConfig) -> CompletionResult:
        """非流式完成。

        Args:
            config: 统一的完成请求配置

        Returns:
            统一的完成结果

        Raises:
            LLMAdapterError: 请求失败
        """

    @abstractmethod
    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]:
        """流式完成。

        返回统一的 StreamEvent 流，同时保留原始 provider 事件。
        调用方可以选择：
        - 读取 StreamEvent 获取归一化的事件
        - 通过 StreamEvent.provider_event 访问原始事件

        Args:
            config: 统一的完成请求配置

        Yields:
            StreamEvent: 归一化的流式事件

        Raises:
            LLMAdapterError: 请求失败
        """

    @abstractmethod
    def get_provider_info(self) -> ProviderInfo:
        """返回 provider 描述信息。"""

    @abstractmethod
    async def health_check(self) -> bool:
        """检查 provider 是否可用。

        用于 circuit breaker 和 fallback 路由决策。
        应该是轻量级操作（如发一个短请求或检查连接）。
        """

    @abstractmethod
    async def close(self) -> None:
        """关闭底层连接（httpx client 等）。"""

    async def __aenter__(self) -> ILLMAdapter:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


class LLMAdapterError(Exception):
    """LLM Adapter 异常基类。"""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        status_code: int | None = None,
        retry_after: float | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retry_after = retry_after
        self.retryable = retryable


class RateLimitError(LLMAdapterError):
    """速率限制错误 (429)。"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        provider: str = "",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message,
            provider=provider,
            status_code=429,
            retry_after=retry_after,
            retryable=True,
        )


class ServiceUnavailableError(LLMAdapterError):
    """服务不可用错误 (5xx)。"""

    def __init__(
        self,
        message: str = "Service unavailable",
        *,
        provider: str = "",
        status_code: int = 503,
    ) -> None:
        super().__init__(
            message,
            provider=provider,
            status_code=status_code,
            retryable=True,
        )


class InvalidRequestError(LLMAdapterError):
    """无效请求错误 (400)。不应重试。"""

    def __init__(
        self,
        message: str = "Invalid request",
        *,
        provider: str = "",
    ) -> None:
        super().__init__(
            message,
            provider=provider,
            status_code=400,
            retryable=False,
        )


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
