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

import json
import logging
import os
from collections.abc import AsyncIterator

import httpx

from ..base import (
    ILLMAdapter,
    InvalidRequestError,
    LLMAdapterError,
    RateLimitError,
    ServiceUnavailableError,
)
from ..types import (
    CompletionConfig,
    CompletionResult,
    ContentBlock,
    ImageBlock,
    Message,
    ProviderInfo,
    StopReason,
    StreamEvent,
    StreamEventType,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolDefinition,
    ToolMessage,
    ToolParameterSchema,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
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


def _convert_messages(messages: list[Message]) -> list[dict]:
    """将内部统一消息格式转换为 DeepSeek/OpenAI 格式。

    关键转换：
    - ToolMessage(role="tool") → OpenAI tool role message
    - ContentBlock 数组 → OpenAI content parts
    - ToolUseBlock → OpenAI tool_calls
    - ToolResultBlock → OpenAI tool result
    - ThinkingBlock → 附加 reasoning_content 字段（回传时使用）
    """
    result: list[dict] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})

        elif isinstance(msg, ToolMessage):
            result.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": msg.content,
            })

        elif isinstance(msg, type) and msg == SystemMessage:
            continue

        else:
            # UserMessage or AssistantMessage — content is list[ContentBlock]
            content = msg.content if isinstance(msg.content, list) else []

            # 提取 text 和 reasoning_content
            text_parts: list[str] = []
            reasoning_parts: list[str] = []
            tool_calls: list[dict] = []
            tool_results: list[dict] = []

            for block in content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
                elif isinstance(block, ThinkingBlock):
                    reasoning_parts.append(block.thinking)
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input, ensure_ascii=False),
                        },
                    })
                elif isinstance(block, ToolResultBlock):
                    tool_results.append({
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                        "is_error": block.is_error,
                    })

            # 处理 tool_result blocks：转换为独立的 tool role 消息
            for tr in tool_results:
                result.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_use_id"],
                    "content": tr["content"],
                })

            if tool_calls:
                # assistant message with tool calls
                entry: dict = {
                    "role": "assistant",
                    "content": " ".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls,
                }
                # DeepSeek V4: tool call 场景必须回传 reasoning_content
                if reasoning_parts:
                    entry["reasoning_content"] = "\n".join(reasoning_parts)
                result.append(entry)
            elif tool_results:
                # tool results already handled above
                continue
            else:
                # 普通消息
                text = "\n".join(text_parts) if text_parts else ""
                if isinstance(msg, type):  # shouldn't happen
                    continue

                role = msg.role
                entry = {"role": role, "content": text}

                # 非工具调用的 assistant 消息也保留 reasoning_content（回传需要）
                if reasoning_parts and role == "assistant":
                    entry["reasoning_content"] = "\n".join(reasoning_parts)

                result.append(entry)

    return result


def _convert_tools(tools: list[ToolDefinition]) -> list[dict]:
    """将统一工具定义转换为 OpenAI function calling 格式。"""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters.model_dump(exclude_none=True),
            },
        }
        for t in tools
    ]


def _build_request_body(config: CompletionConfig) -> dict:
    """构建 DeepSeek/OpenAI 兼容的请求体。"""
    body: dict = {
        "model": config.model,
        "messages": _convert_messages(config.messages),
        "stream": config.stream,
    }

    if config.tools:
        body["tools"] = _convert_tools(config.tools)

    # 基础采样参数（thinking 模式下会自动剥离）
    if config.temperature is not None:
        body["temperature"] = config.temperature
    if config.max_tokens is not None:
        body["max_tokens"] = config.max_tokens
    if config.top_p is not None:
        body["top_p"] = config.top_p
    if config.stop:
        body["stop"] = config.stop

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
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage_data = data.get("usage", {})

    # 解析 content blocks
    content_blocks: list[ContentBlock] = []

    # 文本内容
    text = message.get("content")
    if text:
        content_blocks.append(TextBlock(text=text))

    # reasoning_content → ThinkingBlock
    reasoning = message.get("reasoning_content")
    if reasoning:
        content_blocks.append(ThinkingBlock(thinking=reasoning))

    # tool_calls → ToolUseBlock
    for tc in message.get("tool_calls", []):
        func = tc.get("function", {})
        args_str = func.get("arguments", "{}")
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {"_raw_arguments": args_str}

        content_blocks.append(
            ToolUseBlock(
                id=tc.get("id", ""),
                name=func.get("name", ""),
                input=args,
            )
        )

    # 停止原因映射
    finish_reason = choice.get("finish_reason", "")
    stop_map = {
        "stop": StopReason.END_TURN,
        "length": StopReason.MAX_TOKENS,
        "tool_calls": StopReason.TOOL_USE,
        "content_filter": StopReason.END_TURN,
    }
    stop_reason = stop_map.get(finish_reason, StopReason.END_TURN)

    # usage 统计
    usage = UsageStats(
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
        cache_read_tokens=usage_data.get("prompt_tokens_details", {}).get(
            "cached_tokens", 0
        ),
    )

    return CompletionResult(
        id=data.get("id", ""),
        model=data.get("model", ""),
        content=content_blocks,
        stop_reason=stop_reason,
        usage=usage,
        raw_response=data,
    )


def _handle_error(response: httpx.Response) -> None:
    """将 HTTP 错误转换为对应的 LLMAdapterError。"""
    status = response.status_code

    try:
        body = response.json()
        message = body.get("error", {}).get("message", response.text)
    except Exception:
        message = response.text

    if status == 429:
        retry_after = response.headers.get("retry-after")
        raise RateLimitError(
            message,
            provider="deepseek",
            retry_after=float(retry_after) if retry_after else None,
        )

    if status >= 500:
        raise ServiceUnavailableError(
            message,
            provider="deepseek",
            status_code=status,
        )

    if status >= 400:
        raise InvalidRequestError(message, provider="deepseek")


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
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "DeepSeek API key required. "
                "Set DEEPSEEK_API_KEY env var or pass api_key parameter."
            )

        self._base_url = base_url.rstrip("/")  # 确保没有尾随斜杠
        self._default_model = default_model
        self._client = httpx.AsyncClient(  # 初始化异步客户端
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=10.0,
                pool=timeout,
            ),
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
        """流式输出"""
        _validate_no_image_blocks(config.messages)

        body = _build_request_body(config)
        body["stream"] = True

        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=body
            ) as response:
                if response.status_code != 200:
                    # 读取完整错误响应
                    error_body = await response.aread()
                    error_resp = httpx.Response(
                        status_code=response.status_code,
                        content=error_body,
                        headers=response.headers,
                    )
                    _handle_error(error_resp)

                text_buffer = ""
                tool_calls_buffer: dict[int, dict] = {}

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        yield StreamEvent(type=StreamEventType.DONE)
                        break

                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    # 保留原始事件
                    raw_event = chunk

                    # 解析 delta
                    choices = chunk.get("choices", [])
                    if not choices:
                        # usage chunk
                        usage = chunk.get("usage")
                        if usage:
                            yield StreamEvent(
                                type=StreamEventType.USAGE,
                                data={"usage": usage},
                                provider_event=raw_event,
                            )
                        continue

                    delta = choices[0].get("delta", {})
                    finish_reason = choices[0].get("finish_reason")

                    # 文本 delta
                    content = delta.get("content")
                    if content:
                        text_buffer += content
                        yield StreamEvent(
                            type=StreamEventType.TEXT_DELTA,
                            data={"text": content},
                            provider_event=raw_event,
                        )

                    # reasoning_content delta
                    reasoning = delta.get("reasoning_content")
                    if reasoning:
                        yield StreamEvent(
                            type=StreamEventType.THINKING_DELTA,
                            data={"thinking": reasoning},
                            provider_event=raw_event,
                        )

                    # tool_calls delta
                    for tc in delta.get("tool_calls", []):
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tc.get("id", ""),
                                "function": {"name": "", "arguments": ""},
                            }
                            yield StreamEvent(
                                type=StreamEventType.TOOL_USE_START,
                                data={"index": idx, "id": tc.get("id", "")},
                                provider_event=raw_event,
                            )

                        func_delta = tc.get("function", {})
                        if func_delta.get("name"):
                            tool_calls_buffer[idx]["function"]["name"] += func_delta["name"]
                        if func_delta.get("arguments"):
                            tool_calls_buffer[idx]["function"]["arguments"] += func_delta["arguments"]

                        yield StreamEvent(
                            type=StreamEventType.TOOL_USE_DELTA,
                            data={
                                "index": idx,
                                "arguments_delta": func_delta.get("arguments", ""),
                            },
                            provider_event=raw_event,
                        )

                    if finish_reason:
                        # 结束：输出完整的 tool calls
                        for idx, tc in tool_calls_buffer.items():
                            try:
                                args = json.loads(tc["function"]["arguments"])
                            except json.JSONDecodeError:
                                args = {"_raw": tc["function"]["arguments"]}
                            yield StreamEvent(
                                type=StreamEventType.TOOL_USE_END,
                                data={
                                    "index": idx,
                                    "id": tc["id"],
                                    "name": tc["function"]["name"],
                                    "input": args,
                                },
                                provider_event=raw_event,
                            )

                        usage = chunk.get("usage")
                        if usage:
                            yield StreamEvent(
                                type=StreamEventType.USAGE,
                                data={"usage": usage},
                                provider_event=raw_event,
                            )

                        yield StreamEvent(type=StreamEventType.DONE)
                        break

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
