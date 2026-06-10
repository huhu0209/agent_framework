"""DeepSeek V4 Provider。

DeepSeek V4 同时支持 OpenAI ChatCompletions 和 Anthropic Messages 两套协议。
本实现使用 OpenAI 兼容接口，因为：
1. DeepSeek 的 OpenAI 兼容更成熟
2. 流式处理更简单（单一 delta 流）
3. 后续 OpenAI provider 可复用大量代码

DeepSeek V4 特殊处理：
- reasoning_content: 非标准字段，tool call 场景必须回传
- thinking 模式: extra_body={"thinking": {"type": "enabled"}}
- reasoning_effort: "high" / "max"（不是 OpenAI 的 low/medium/high）
- 纯文本: 不支持 vision，需要拒绝 image block
- 参数静默失效: thinking 模式下 temperature/top_p/presence/frequency_penalty 无效
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator

import httpx
from pydantic import SecretStr

from ..base import (
    ILLMAdapter,
    InvalidRequestError,
    ServiceUnavailableError,
    handle_http_error,
)
from ..streaming import OpenAIStreamParser, parse_sse_lines
from ..transform import (
    build_openai_sampling_params,
    messages_to_deepseek,
    parse_deepseek_response,
    tools_to_openai,
)
from ..types import (
    CompletionConfig,
    CompletionResult,
    ImageBlock,
    Message,
    ProviderInfo,
    StreamEvent,
    StreamEventType,
)

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-pro"


def _validate_no_image_blocks(messages: list[Message]) -> None:
    """DeepSeek 不支持视觉，拒绝所有 image block。"""
    for msg in messages:
        content = msg.content if hasattr(msg, "content") and isinstance(msg.content, list) else []
        for block in content:
            if isinstance(block, ImageBlock):
                raise InvalidRequestError(
                    "DeepSeek does not support image input. "
                    "Remove ImageBlock from messages.",
                    provider="deepseek",
                )


def _build_request_body(config: CompletionConfig) -> dict:
    """构建 DeepSeek/OpenAI 兼容的请求体。"""
    body: dict = {
        "model": config.model,
        "messages": messages_to_deepseek(config.messages),
        "stream": config.stream,
    }

    if config.tools:
        body["tools"] = tools_to_openai(config.tools)

    # 基础采样参数
    sampling = build_openai_sampling_params(config)
    body.update(sampling)

    # Thinking 模式配置
    if config.thinking and config.thinking.type == "enabled":
        body["thinking"] = {"type": "enabled"}

        # thinking 模式下这些参数静默无效，发出警告
        silent_keys = ["temperature", "top_p", "presence_penalty", "frequency_penalty"]
        for key in silent_keys:
            if key in body:
                logger.warning(
                    "DeepSeek: '%s' is silently ignored in thinking mode", key
                )

    # Provider 扩展参数
    if config.provider_extras:
        # reasoning_effort: DeepSeek 只接受 "high" / "max"
        if "reasoning_effort" in config.provider_extras:
            effort = config.provider_extras["reasoning_effort"]
            if effort not in ("high", "max"):
                logger.warning(
                    "DeepSeek: reasoning_effort '%s' not supported, "
                    "use 'high' or 'max'. Mapping to 'high'.",
                    effort,
                )
                effort = "high"
            body["reasoning_effort"] = effort

        # 其他扩展直接合并
        for key, value in config.provider_extras.items():
            if key not in ("reasoning_effort",):
                body[key] = value

    return body


def _parse_response(data: dict) -> CompletionResult:
    """解析 DeepSeek/OpenAI 响应为统一 CompletionResult。"""
    blocks, stop_reason, usage = parse_deepseek_response(data)

    return CompletionResult(
        id=data.get("id", ""),
        model=data.get("model", ""),
        content=blocks,
        stop_reason=stop_reason,
        usage=usage,
        raw_response=data,
    )


def _handle_error(response: httpx.Response) -> None:
    handle_http_error(response, "deepseek")


class DeepSeekProvider(ILLMAdapter):
    """DeepSeek V4 Provider (OpenAI 兼容接口)。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEEPSEEK_BASE_URL,
        default_model: str = DEEPSEEK_DEFAULT_MODEL,
        timeout: float = 120.0,
    ) -> None:
        raw_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not raw_key:
            raise ValueError(
                "DeepSeek API key required. "
                "Set DEEPSEEK_API_KEY env var or pass api_key parameter."
            )

        self._api_key = SecretStr(raw_key)
        self._base_url = base_url.rstrip("/")  # 确保没有尾随斜杠
        self._default_model = default_model
        self._client = httpx.AsyncClient(  # 初始化异步客户端
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=10.0,
                pool=timeout,
            ),
            proxy=None,
        )

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        _validate_no_image_blocks(config.messages)

        body = _build_request_body(config)

        try:
            response = await self._client.post("/chat/completions", json=body)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableError(
                f"Request timeout: {exc}",
                provider="deepseek",
            ) from exc
        except httpx.ConnectError as exc:
            raise ServiceUnavailableError(
                f"Connection failed: {exc}",
                provider="deepseek",
            ) from exc

        if response.status_code != 200:
            _handle_error(response)

        data = response.json()
        return _parse_response(data)

    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]:
        """流式输出。"""
        _validate_no_image_blocks(config.messages)

        body = _build_request_body(config)
        body["stream"] = True

        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=body
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_resp = httpx.Response(
                        status_code=response.status_code,
                        content=error_body,
                        headers=response.headers,
                    )
                    _handle_error(error_resp)

                parser = OpenAIStreamParser()
                async for chunk in parse_sse_lines(response.aiter_lines()):
                    for event in parser.parse_chunk(chunk):
                        yield event

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={"error": str(exc)},
            )

    def get_provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="deepseek",
            base_url=self._base_url,
            supported_features=[
                "chat",
                "streaming",
                "tool_calling",
                "thinking",
                "reasoning_content",
            ],
            default_model=self._default_model,
            max_context_tokens=1000000,
            max_output_tokens=8192,
        )

    async def health_check(self) -> bool:
        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._default_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> DeepSeekProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
