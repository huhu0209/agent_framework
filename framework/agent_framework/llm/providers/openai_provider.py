"""OpenAI Chat Completions Provider。

OpenAI 是生态中心，协议最标准。与 DeepSeek 的主要区别：
- 无 reasoning_content 字段（o 系列隐藏思考过程）
- 支持 reasoning_effort: minimal/low/medium/high
- 支持原生 structured output (json_schema strict)
- 支持 vision (image input)
- 支持 logprobs

代码大量复用 transform.py 和 streaming.py 中的共享逻辑。
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator

import httpx
from pydantic import SecretStr

from ..base import (
    ILLMAdapter,
    InvalidRequestError,
    LLMAdapterError,
    RateLimitError,
    ServiceUnavailableError,
    handle_http_error,
)
from ..streaming import OpenAIStreamParser, parse_sse_lines
from ..transform import (
    build_openai_sampling_params,
    messages_to_openai,
    parse_openai_response,
    tools_to_openai,
)
from ..types import (
    CompletionConfig,
    CompletionResult,
    Message,
    ProviderInfo,
    StreamEvent,
    StreamEventType,
    UsageStats,
)

logger = logging.getLogger(__name__)

OPENAI_BASE_URL = "https://api.openseek.com/v1"
OPENAI_DEFAULT_MODEL = "gpt-5"


def _build_request_body(config: CompletionConfig) -> dict:
    """构建 OpenAI Chat Completions 请求体。"""
    body: dict = {
        "model": config.model,
        "messages": messages_to_openai(config.messages),
        "stream": config.stream,
    }

    if config.tools:
        body["tools"] = tools_to_openai(config.tools)

    # 采样参数
    sampling = build_openai_sampling_params(config)
    body.update(sampling)

    # reasoning_effort (o 系列模型)
    if config.thinking and config.thinking.type == "enabled":
        effort = config.provider_extras.get("reasoning_effort", "high")
        body["reasoning_effort"] = effort

    # Provider 扩展参数
    if config.provider_extras:
        for key, value in config.provider_extras.items():
            if key not in ("reasoning_effort",):
                body[key] = value

    return body


def _parse_response(data: dict) -> CompletionResult:
    """解析 OpenAI 响应为统一 CompletionResult。"""
    blocks, stop_reason, usage = parse_openai_response(data)

    return CompletionResult(
        id=data.get("id", ""),
        model=data.get("model", ""),
        content=blocks,
        stop_reason=stop_reason,
        usage=usage,
        raw_response=data,
    )


def _handle_error(response: httpx.Response) -> None:
    handle_http_error(response, "openai")


class OpenAIProvider(ILLMAdapter):
    """OpenAI Chat Completions Provider。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = OPENAI_BASE_URL,
        default_model: str = OPENAI_DEFAULT_MODEL,
        timeout: float = 120.0,
    ) -> None:
        raw_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not raw_key:
            raise ValueError(
                "OpenAI API key required. "
                "Set OPENAI_API_KEY env var or pass api_key parameter."
            )

        self._api_key = SecretStr(raw_key)
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._client = httpx.AsyncClient(
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
        body = _build_request_body(config)

        try:
            response = await self._client.post("/chat/completions", json=body)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableError(
                f"Request timeout: {exc}", provider="openai",
            ) from exc
        except httpx.ConnectError as exc:
            raise ServiceUnavailableError(
                f"Connection failed: {exc}", provider="openai",
            ) from exc

        if response.status_code != 200:
            _handle_error(response)

        body = response.text
        if not body or not body.strip():
            raise LLMAdapterError(
                "LLM returned 200 OK with empty body", provider="openai",
            )

        return _parse_response(response.json())

    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]:
        body = _build_request_body(config)
        body["stream"] = True

        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=body,
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
            name="openai",
            base_url=self._base_url,
            supported_features=[
                "chat",
                "streaming",
                "tool_calling",
                "vision",
                "structured_output",
                "reasoning_effort",
            ],
            default_model=self._default_model,
            max_context_tokens=400000,
            max_output_tokens=16384,
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

    async def __aenter__(self) -> OpenAIProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
