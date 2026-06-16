"""Anthropic Messages API Provider。

Anthropic 是协议差异最大的 provider，也是 coding agent 必备的。
关键差异：
- system 是顶层字段，不在 messages 数组里
- tool_use / tool_result 是 content block，不是独立角色
- arguments 是 object（不 stringify）
- extended thinking 有 budget_tokens 精确控制和 signature 回传校验
- cache_control 显式缓存断点
- 不支持原生 structured output（需通过强制 tool 调用实现）
- 流式事件类型多（message_start / content_block_start / delta / stop）

Anthropic 流式是按 content_block_index 维护多个并行流，
比 OpenAI/DeepSeek 的单一 delta 流复杂得多。
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
    ServiceUnavailableError,
    handle_http_error,
)
from ..streaming import parse_sse_lines
from ..transform import (
    messages_to_anthropic,
    parse_anthropic_response,
    tools_to_anthropic,
)
from ..types import (
    CompletionConfig,
    CompletionResult,
    ProviderInfo,
    StreamEvent,
    StreamEventType,
    UsageStats,
)

logger = logging.getLogger(__name__)

ANTHROPIC_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6-20250514"
# Extended thinking 默认 budget（config.thinking.budget_tokens 未配置时）
DEFAULT_THINKING_BUDGET = 16000
# thinking 开启时的 max_tokens 额外预留（输出配额，须 >= budget）
DEFAULT_MAX_TOKENS_RESERVE = 8192


def _build_request_body(config: CompletionConfig) -> dict:
    """构建 Anthropic Messages API 请求体。"""
    system_prompt, anthropic_messages = messages_to_anthropic(config.messages)

    body: dict = {
        "model": config.model,
        "messages": anthropic_messages,
        "max_tokens": config.max_tokens or 8192,
    }

    if system_prompt:
        body["system"] = system_prompt

    if config.tools:
        body["tools"] = tools_to_anthropic(config.tools)

    # 采样参数
    if config.temperature is not None:
        body["temperature"] = config.temperature
    if config.top_p is not None:
        body["top_p"] = config.top_p
    if config.stop:
        body["stop_sequences"] = config.stop

    # Extended thinking
    if config.thinking and config.thinking.type == "enabled":
        budget = config.thinking.budget_tokens or DEFAULT_THINKING_BUDGET
        body["thinking"] = {
            "type": "enabled",
            "budget_tokens": budget,
        }
        # max_tokens 必须 >= budget_tokens + 输出
        if config.max_tokens is None:
            body["max_tokens"] = budget + DEFAULT_MAX_TOKENS_RESERVE

    # Provider 扩展参数（如 cache_control、betas 等）
    if config.provider_extras:
        for key, value in config.provider_extras.items():
            body[key] = value

    return body


def _parse_response(data: dict) -> CompletionResult:
    """解析 Anthropic Messages API 响应。"""
    blocks, stop_reason, usage = parse_anthropic_response(data)

    return CompletionResult(
        id=data.get("id", ""),
        model=data.get("model", ""),
        content=blocks,
        stop_reason=stop_reason,
        usage=usage,
        raw_response=data,
    )


def _handle_error(response: httpx.Response) -> None:
    handle_http_error(response, "anthropic")


# ============================================================
# Anthropic 流式解析
# ============================================================


class AnthropicStreamParser:
    """Anthropic Messages API 流式响应解析器。

    Anthropic 的流式事件类型：
    - message_start: 包含 message 元数据
    - content_block_start: 新 content block 开始 (text/tool_use/thinking)
    - content_block_delta: 增量内容 (text_delta/input_json_delta/thinking_delta)
    - content_block_stop: content block 结束
    - message_delta: 最终 stop_reason 和 usage
    - message_stop: 消息结束

    必须按 content_block_index 维护多个并行 block 的状态。
    """

    def __init__(self) -> None:
        self._blocks: dict[int, dict] = {}  # index -> {type, text, id, name, input_json, thinking}
        self._usage = UsageStats()
        self._model = ""

    def parse_event(self, event_type: str, data: dict) -> list[StreamEvent]:
        """解析一个 Anthropic SSE 事件。"""
        events: list[StreamEvent] = []

        if event_type == "message_start":
            msg = data.get("message", {})
            self._model = msg.get("model", "")
            usage = msg.get("usage", {})
            self._usage = UsageStats(
                input_tokens=usage.get("input_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                cache_write_tokens=usage.get("cache_creation_input_tokens", 0),
            )

        elif event_type == "content_block_start":
            idx = data.get("index", 0)
            block = data.get("content_block", {})
            block_type = block.get("type")

            self._blocks[idx] = {
                "type": block_type,
                "text": "",
                "thinking": "",
                "id": block.get("id", ""),
                "name": block.get("name", ""),
                "input_json": "",
            }

            if block_type == "tool_use":
                events.append(StreamEvent(
                    type=StreamEventType.TOOL_USE_START,
                    data={"index": idx, "id": block.get("id", ""), "name": block.get("name", "")},
                    provider_event=data,
                ))

        elif event_type == "content_block_delta":
            idx = data.get("index", 0)
            delta = data.get("delta", {})
            delta_type = delta.get("type")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                events.append(StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    data={"text": text},
                    provider_event=data,
                ))

            elif delta_type == "thinking_delta":
                thinking = delta.get("thinking", "")
                events.append(StreamEvent(
                    type=StreamEventType.THINKING_DELTA,
                    data={"thinking": thinking},
                    provider_event=data,
                ))

            elif delta_type == "input_json_delta":
                json_str = delta.get("partial_json", "")
                if idx in self._blocks:
                    self._blocks[idx]["input_json"] += json_str
                events.append(StreamEvent(
                    type=StreamEventType.TOOL_USE_DELTA,
                    data={"index": idx, "arguments_delta": json_str},
                    provider_event=data,
                ))

        elif event_type == "message_delta":
            delta = data.get("delta", {})
            usage = data.get("usage", {})

            self._usage = UsageStats(
                input_tokens=self._usage.input_tokens,
                output_tokens=usage.get("output_tokens", 0),
                cache_read_tokens=self._usage.cache_read_tokens,
                cache_write_tokens=self._usage.cache_write_tokens,
                thinking_tokens=usage.get("thinking_tokens", 0),
            )

            events.append(StreamEvent(
                type=StreamEventType.USAGE,
                data={"usage": {
                    "input_tokens": self._usage.input_tokens,
                    "output_tokens": self._usage.output_tokens,
                }},
                provider_event=data,
            ))

            # 输出完整的 tool calls
            for idx, block in self._blocks.items():
                if block["type"] == "tool_use":
                    try:
                        args = json.loads(block["input_json"]) if block["input_json"] else {}
                    except json.JSONDecodeError:
                        args = {"_raw": block["input_json"]}
                    events.append(StreamEvent(
                        type=StreamEventType.TOOL_USE_END,
                        data={"index": idx, "id": block["id"], "name": block["name"], "input": args},
                        provider_event=data,
                    ))

            events.append(StreamEvent(type=StreamEventType.DONE))

        return events


class AnthropicProvider(ILLMAdapter):
    """Anthropic Messages API Provider。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = ANTHROPIC_BASE_URL,
        default_model: str = ANTHROPIC_DEFAULT_MODEL,
        timeout: float = 120.0,
    ) -> None:
        raw_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not raw_key:
            raise ValueError(
                "Anthropic API key required. "
                "Set ANTHROPIC_API_KEY env var or pass api_key parameter."
            )

        self._api_key = SecretStr(raw_key)
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "x-api-key": self._api_key.get_secret_value(),
                "anthropic-version": "2023-06-01",
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
            response = await self._client.post("/v1/messages", json=body)
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableError(
                f"Request timeout: {exc}", provider="anthropic",
            ) from exc
        except httpx.ConnectError as exc:
            raise ServiceUnavailableError(
                f"Connection failed: {exc}", provider="anthropic",
            ) from exc

        if response.status_code != 200:
            _handle_error(response)

        return _parse_response(response.json())

    async def stream(self, config: CompletionConfig) -> AsyncIterator[StreamEvent]:
        body = _build_request_body(config)
        body["stream"] = True

        try:
            async with self._client.stream(
                "POST", "/v1/messages", json=body,
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_resp = httpx.Response(
                        status_code=response.status_code,
                        content=error_body,
                        headers=response.headers,
                    )
                    _handle_error(error_resp)

                parser = AnthropicStreamParser()

                async for chunk in parse_sse_lines(response.aiter_lines()):
                    event_type = chunk.get("type", "")
                    for event in parser.parse_event(event_type, chunk):
                        yield event

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={"error": str(exc)},
            )

    def get_provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="anthropic",
            base_url=self._base_url,
            supported_features=[
                "chat",
                "streaming",
                "tool_calling",
                "vision",
                "thinking",
                "cache_control",
                "pdf",
                "computer_use",
            ],
            default_model=self._default_model,
            max_context_tokens=200000,
            max_output_tokens=8192,
        )

    async def health_check(self) -> bool:
        try:
            response = await self._client.post(
                "/v1/messages",
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

    async def __aenter__(self) -> AnthropicProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
