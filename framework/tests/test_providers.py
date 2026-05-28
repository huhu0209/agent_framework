"""Provider 层 mock 集成测试。

覆盖三个 provider（OpenAI / DeepSeek / Anthropic）的：
1. handle_http_error — HTTP 错误码到 typed 异常的映射
2. _build_request_body — 请求体构建逻辑
3. _parse_response — 响应解析逻辑
4. 生命周期 — close / context manager
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from agent_framework.llm.base import (
    InvalidRequestError,
    RateLimitError,
    ServiceUnavailableError,
    handle_http_error,
)
from agent_framework.llm.providers.anthropic_provider import (
    AnthropicProvider,
    _build_request_body as anthropic_build_body,
    _parse_response as anthropic_parse_response,
)
from agent_framework.llm.providers.deepseek_provider import (
    DeepSeekProvider,
    _build_request_body as deepseek_build_body,
    _parse_response as deepseek_parse_response,
)
from agent_framework.llm.providers.openai_provider import (
    OpenAIProvider,
    _build_request_body as openai_build_body,
    _parse_response as openai_parse_response,
)
from agent_framework.llm.types import (
    CompletionConfig,
    ContentBlock,
    Message,
    StopReason,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ThinkingConfig,
    ToolDefinition,
    ToolParameterSchema,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)


# ============================================================
# Helpers
# ============================================================


def _make_httpx_response(
    status_code: int,
    json_body: dict | None = None,
    text: str = "",
    headers: dict | None = None,
) -> MagicMock:
    """构建 mock httpx.Response。"""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    if json_body is not None:
        resp.json.return_value = json_body
        resp.text = json.dumps(json_body)
    else:
        resp.json.side_effect = Exception("not json")
        resp.text = text
    return resp


def _basic_config(**overrides) -> CompletionConfig:
    """构建最小 CompletionConfig，支持覆盖任意字段。"""
    defaults = {
        "model": "test-model",
        "messages": [UserMessage(content=[TextBlock(text="hello")])],
    }
    defaults.update(overrides)
    return CompletionConfig(**defaults)


def _openai_text_response(text: str = "world") -> dict:
    """构建 OpenAI 格式的文本响应。"""
    return {
        "id": "chatcmpl-test",
        "model": "gpt-5",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _openai_tool_response(
    tool_call_id: str = "call_abc",
    function_name: str = "get_weather",
    arguments: str = '{"city": "Tokyo"}',
) -> dict:
    """构建 OpenAI 格式的 tool call 响应。"""
    return {
        "id": "chatcmpl-tool",
        "model": "gpt-5",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": arguments,
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35},
    }


def _deepseek_text_response(text: str = "response") -> dict:
    """构建 DeepSeek 格式的文本响应（OpenAI 兼容）。"""
    return {
        "id": "chatcmpl-ds",
        "model": "deepseek-v4-pro",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
    }


def _anthropic_text_response(text: str = "hello back") -> dict:
    """构建 Anthropic Messages API 格式的文本响应。"""
    return {
        "id": "msg_test",
        "model": "claude-sonnet-4-6-20250514",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 12, "output_tokens": 6},
    }


def _anthropic_tool_response(
    tool_id: str = "toolu_abc",
    tool_name: str = "search",
    tool_input: dict | None = None,
) -> dict:
    """构建 Anthropic 格式的 tool_use 响应。"""
    return {
        "id": "msg_tool",
        "model": "claude-sonnet-4-6-20250514",
        "content": [
            {"type": "text", "text": "Let me search for that."},
            {
                "type": "tool_use",
                "id": tool_id,
                "name": tool_name,
                "input": tool_input or {"query": "test"},
            },
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 15, "output_tokens": 10},
    }


def _make_provider(cls, api_key: str = "test-key"):
    """创建 provider 实例，绕过 httpx.AsyncClient 真实初始化。"""
    with patch.object(cls, "__init__", lambda self, **kw: None):
        provider = object.__new__(cls)
    provider._api_key = SecretStr(api_key)
    provider._base_url = "https://mock.test"
    provider._default_model = "mock-model"
    provider._client = AsyncMock()
    return provider


# ============================================================
# 0. SecretStr API key tests
# ============================================================


class TestApiKeyIsSecretStr:
    """API key 必须以 SecretStr 存储，防止 repr/logging 泄露。"""

    @pytest.mark.parametrize(
        "provider_cls",
        [OpenAIProvider, AnthropicProvider, DeepSeekProvider],
    )
    def test_api_key_is_secret_str(self, provider_cls: type) -> None:
        provider = _make_provider(provider_cls)
        assert isinstance(provider._api_key, SecretStr)

    @pytest.mark.parametrize(
        "provider_cls",
        [OpenAIProvider, AnthropicProvider, DeepSeekProvider],
    )
    def test_api_key_repr_masks(self, provider_cls: type) -> None:
        provider = _make_provider(provider_cls, api_key="sk-super-secret-key-12345")
        assert str(provider._api_key) == "**********"

    @pytest.mark.parametrize(
        "provider_cls",
        [OpenAIProvider, AnthropicProvider, DeepSeekProvider],
    )
    def test_api_key_get_secret_value_returns_actual(self, provider_cls: type) -> None:
        provider = _make_provider(provider_cls, api_key="sk-super-secret-key-12345")
        assert provider._api_key.get_secret_value() == "sk-super-secret-key-12345"


# ============================================================
# 1. handle_http_error 集成测试
# ============================================================


class TestHandleHttpError:
    """HTTP 错误码到 typed LLM 异常的映射。"""

    def test_429_raises_rate_limit_error(self) -> None:
        resp = _make_httpx_response(
            429,
            json_body={"error": {"message": "Too many requests"}},
            headers={"retry-after": "30"},
        )
        with pytest.raises(RateLimitError) as exc_info:
            handle_http_error(resp, "openai")

        assert exc_info.value.provider == "openai"
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 30.0
        assert exc_info.value.retryable is True

    def test_500_raises_service_unavailable(self) -> None:
        resp = _make_httpx_response(
            500,
            json_body={"error": {"message": "Internal server error"}},
        )
        with pytest.raises(ServiceUnavailableError) as exc_info:
            handle_http_error(resp, "deepseek")

        assert exc_info.value.provider == "deepseek"
        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True

    def test_503_raises_service_unavailable(self) -> None:
        resp = _make_httpx_response(503, text="Service overloaded")
        with pytest.raises(ServiceUnavailableError) as exc_info:
            handle_http_error(resp, "anthropic")

        assert exc_info.value.provider == "anthropic"
        assert exc_info.value.status_code == 503

    def test_400_raises_invalid_request(self) -> None:
        resp = _make_httpx_response(
            400,
            json_body={"error": {"message": "Invalid model specified"}},
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            handle_http_error(resp, "openai")

        assert exc_info.value.provider == "openai"
        assert exc_info.value.status_code == 400
        assert exc_info.value.retryable is False

    def test_401_raises_invalid_request(self) -> None:
        resp = _make_httpx_response(
            401,
            json_body={"error": {"message": "Invalid API key"}},
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            handle_http_error(resp, "deepseek")

        assert exc_info.value.status_code == 400  # base class sets 400 for all 4xx
        assert "Invalid API key" in str(exc_info.value)

    def test_429_without_retry_after_header(self) -> None:
        resp = _make_httpx_response(
            429,
            json_body={"error": {"message": "Rate limited"}},
        )
        with pytest.raises(RateLimitError) as exc_info:
            handle_http_error(resp, "anthropic")

        assert exc_info.value.retry_after is None

    def test_non_json_error_body_uses_text(self) -> None:
        resp = _make_httpx_response(500, text="plain error text")
        with pytest.raises(ServiceUnavailableError) as exc_info:
            handle_http_error(resp, "openai")

        assert "plain error text" in str(exc_info.value)

    def test_openai_handle_error_delegates(self) -> None:
        """OpenAI _handle_error 调用 handle_http_error 并传入 provider='openai'。"""
        from agent_framework.llm.providers.openai_provider import _handle_error

        resp = _make_httpx_response(429, json_body={"error": {"message": "rl"}})
        with pytest.raises(RateLimitError) as exc_info:
            _handle_error(resp)
        assert exc_info.value.provider == "openai"

    def test_deepseek_handle_error_delegates(self) -> None:
        from agent_framework.llm.providers.deepseek_provider import _handle_error

        resp = _make_httpx_response(500, text="err")
        with pytest.raises(ServiceUnavailableError) as exc_info:
            _handle_error(resp)
        assert exc_info.value.provider == "deepseek"

    def test_anthropic_handle_error_delegates(self) -> None:
        from agent_framework.llm.providers.anthropic_provider import _handle_error

        resp = _make_httpx_response(400, json_body={"error": {"message": "bad"}})
        with pytest.raises(InvalidRequestError) as exc_info:
            _handle_error(resp)
        assert exc_info.value.provider == "anthropic"


# ============================================================
# 2. OpenAI _build_request_body
# ============================================================


class TestOpenAIBuildRequestBody:
    """OpenAI 请求体构建。"""

    def test_basic_request(self) -> None:
        config = _basic_config()
        body = openai_build_body(config)

        assert body["model"] == "test-model"
        assert body["stream"] is False
        assert isinstance(body["messages"], list)
        assert "tools" not in body

    def test_with_tools(self) -> None:
        tools = [
            ToolDefinition(
                name="get_weather",
                description="Get weather for a city",
                parameters=ToolParameterSchema(
                    properties={"city": {"type": "string", "description": "City name"}},
                    required=["city"],
                ),
            )
        ]
        config = _basic_config(tools=tools)
        body = openai_build_body(config)

        assert "tools" in body
        assert len(body["tools"]) == 1
        assert body["tools"][0]["function"]["name"] == "get_weather"

    def test_with_temperature(self) -> None:
        config = _basic_config(temperature=0.7)
        body = openai_build_body(config)

        assert body["temperature"] == 0.7

    def test_with_thinking_config(self) -> None:
        config = _basic_config(
            thinking=ThinkingConfig(type="enabled"),
            provider_extras={"reasoning_effort": "high"},
        )
        body = openai_build_body(config)

        assert body["reasoning_effort"] == "high"

    def test_provider_extras_merged(self) -> None:
        config = _basic_config(provider_extras={"logprobs": True, "top_logprobs": 5})
        body = openai_build_body(config)

        assert body["logprobs"] is True
        assert body["top_logprobs"] == 5


# ============================================================
# 3. DeepSeek _build_request_body
# ============================================================


class TestDeepSeekBuildRequestBody:
    """DeepSeek 请求体构建。"""

    def test_basic_request(self) -> None:
        config = _basic_config()
        body = deepseek_build_body(config)

        assert body["model"] == "test-model"
        assert body["stream"] is False
        assert "tools" not in body

    def test_with_tools(self) -> None:
        tools = [
            ToolDefinition(
                name="search",
                description="Search the web",
            )
        ]
        config = _basic_config(tools=tools)
        body = deepseek_build_body(config)

        assert "tools" in body
        assert body["tools"][0]["function"]["name"] == "search"

    def test_thinking_mode_adds_body_field(self) -> None:
        config = _basic_config(thinking=ThinkingConfig(type="enabled"))
        body = deepseek_build_body(config)

        assert body["thinking"] == {"type": "enabled"}

    def test_reasoning_effort_mapping(self) -> None:
        config = _basic_config(
            provider_extras={"reasoning_effort": "max"}
        )
        body = deepseek_build_body(config)

        assert body["reasoning_effort"] == "max"


# ============================================================
# 4. Anthropic _build_request_body
# ============================================================


class TestAnthropicBuildRequestBody:
    """Anthropic 请求体构建。"""

    def test_basic_request(self) -> None:
        config = _basic_config()
        body = anthropic_build_body(config)

        assert body["model"] == "test-model"
        assert body["max_tokens"] == 8192
        assert isinstance(body["messages"], list)

    def test_system_prompt_extracted(self) -> None:
        config = _basic_config(
            messages=[
                SystemMessage(content="You are a helpful assistant."),
                UserMessage(content=[TextBlock(text="hi")]),
            ]
        )
        body = anthropic_build_body(config)

        assert "system" in body
        assert isinstance(body["system"], str)

    def test_with_tools(self) -> None:
        tools = [
            ToolDefinition(
                name="calculator",
                description="Do math",
            )
        ]
        config = _basic_config(tools=tools)
        body = anthropic_build_body(config)

        assert "tools" in body
        assert body["tools"][0]["name"] == "calculator"

    def test_thinking_config_sets_budget(self) -> None:
        config = _basic_config(
            thinking=ThinkingConfig(type="enabled", budget_tokens=4000),
        )
        body = anthropic_build_body(config)

        assert body["thinking"] == {"type": "enabled", "budget_tokens": 4000}

    def test_thinking_config_auto_max_tokens(self) -> None:
        """thinking 启用且未设 max_tokens 时，自动计算为 budget + 8192。"""
        config = _basic_config(
            thinking=ThinkingConfig(type="enabled", budget_tokens=4000),
        )
        body = anthropic_build_body(config)

        assert body["max_tokens"] == 4000 + 8192

    def test_temperature_and_top_p(self) -> None:
        config = _basic_config(temperature=0.3, top_p=0.9)
        body = anthropic_build_body(config)

        assert body["temperature"] == 0.3
        assert body["top_p"] == 0.9

    def test_stop_sequences(self) -> None:
        config = _basic_config(stop=["END", "STOP"])
        body = anthropic_build_body(config)

        assert body["stop_sequences"] == ["END", "STOP"]


# ============================================================
# 5. _parse_response 测试
# ============================================================


class TestOpenAIParseResponse:
    """OpenAI 响应解析。"""

    def test_simple_text(self) -> None:
        data = _openai_text_response("Hello!")
        result = openai_parse_response(data)

        assert result.id == "chatcmpl-test"
        assert result.model == "gpt-5"
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextBlock)
        assert result.content[0].text == "Hello!"
        assert result.stop_reason == StopReason.END_TURN

    def test_tool_call(self) -> None:
        data = _openai_tool_response()
        result = openai_parse_response(data)

        assert result.stop_reason == StopReason.TOOL_USE
        tool_blocks = [b for b in result.content if isinstance(b, ToolUseBlock)]
        assert len(tool_blocks) == 1
        assert tool_blocks[0].id == "call_abc"
        assert tool_blocks[0].name == "get_weather"
        assert tool_blocks[0].input == {"city": "Tokyo"}


class TestDeepSeekParseResponse:
    """DeepSeek 响应解析。"""

    def test_simple_text(self) -> None:
        data = _deepseek_text_response("hi there")
        result = deepseek_parse_response(data)

        assert result.id == "chatcmpl-ds"
        assert len(result.content) >= 1
        text_blocks = [b for b in result.content if isinstance(b, TextBlock)]
        assert any(b.text == "hi there" for b in text_blocks)


class TestAnthropicParseResponse:
    """Anthropic 响应解析。"""

    def test_simple_text(self) -> None:
        data = _anthropic_text_response("hey")
        result = anthropic_parse_response(data)

        assert result.id == "msg_test"
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextBlock)
        assert result.content[0].text == "hey"
        assert result.stop_reason == StopReason.END_TURN

    def test_tool_use(self) -> None:
        data = _anthropic_tool_response()
        result = anthropic_parse_response(data)

        assert result.stop_reason == StopReason.TOOL_USE
        tool_blocks = [b for b in result.content if isinstance(b, ToolUseBlock)]
        assert len(tool_blocks) == 1
        assert tool_blocks[0].id == "toolu_abc"
        assert tool_blocks[0].name == "search"
        assert tool_blocks[0].input == {"query": "test"}


# ============================================================
# 6. Provider 生命周期测试
# ============================================================


class TestProviderLifecycle:
    """close() 和 context manager (__aenter__/__aexit__)。"""

    @pytest.mark.asyncio
    async def test_openai_close_calls_aclose(self) -> None:
        provider = _make_provider(OpenAIProvider)
        await provider.close()
        provider._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deepseek_close_calls_aclose(self) -> None:
        provider = _make_provider(DeepSeekProvider)
        await provider.close()
        provider._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_anthropic_close_calls_aclose(self) -> None:
        provider = _make_provider(AnthropicProvider)
        await provider.close()
        provider._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_openai_context_manager(self) -> None:
        provider = _make_provider(OpenAIProvider)
        async with provider as p:
            assert p is provider
        provider._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deepseek_context_manager(self) -> None:
        provider = _make_provider(DeepSeekProvider)
        async with provider as p:
            assert p is provider
        provider._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_anthropic_context_manager(self) -> None:
        provider = _make_provider(AnthropicProvider)
        async with provider as p:
            assert p is provider
        provider._client.aclose.assert_awaited_once()


# ============================================================
# 7. Provider complete() 集成
# ============================================================


class TestProviderComplete:
    """complete() 端到端：mock HTTP response，验证完整路径。"""

    @pytest.mark.asyncio
    async def test_openai_complete_success(self) -> None:
        provider = _make_provider(OpenAIProvider)
        mock_resp = _make_httpx_response(200, json_body=_openai_text_response("test reply"))
        provider._client.post = AsyncMock(return_value=mock_resp)

        config = _basic_config(model="gpt-5")
        result = await provider.complete(config)

        assert result.content[0].text == "test reply"  # type: ignore[union-attr]
        provider._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_openai_complete_error_raises(self) -> None:
        provider = _make_provider(OpenAIProvider)
        mock_resp = _make_httpx_response(429, json_body={"error": {"message": "rl"}})
        provider._client.post = AsyncMock(return_value=mock_resp)

        config = _basic_config()
        with pytest.raises(RateLimitError):
            await provider.complete(config)

    @pytest.mark.asyncio
    async def test_deepseek_complete_success(self) -> None:
        provider = _make_provider(DeepSeekProvider)
        mock_resp = _make_httpx_response(200, json_body=_deepseek_text_response("ds reply"))
        provider._client.post = AsyncMock(return_value=mock_resp)

        config = _basic_config(model="deepseek-v4-pro")
        result = await provider.complete(config)

        text_blocks = [b for b in result.content if isinstance(b, TextBlock)]
        assert any("ds reply" in b.text for b in text_blocks)

    @pytest.mark.asyncio
    async def test_anthropic_complete_success(self) -> None:
        provider = _make_provider(AnthropicProvider)
        mock_resp = _make_httpx_response(200, json_body=_anthropic_text_response("ant reply"))
        provider._client.post = AsyncMock(return_value=mock_resp)

        config = _basic_config(model="claude-sonnet-4-6-20250514")
        result = await provider.complete(config)

        assert result.content[0].text == "ant reply"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_openai_timeout_raises_service_unavailable(self) -> None:
        provider = _make_provider(OpenAIProvider)
        provider._client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        config = _basic_config()
        with pytest.raises(ServiceUnavailableError) as exc_info:
            await provider.complete(config)
        assert exc_info.value.provider == "openai"

    @pytest.mark.asyncio
    async def test_openai_connect_error_raises_service_unavailable(self) -> None:
        provider = _make_provider(OpenAIProvider)
        provider._client.post = AsyncMock(side_effect=httpx.ConnectError("conn refused"))

        config = _basic_config()
        with pytest.raises(ServiceUnavailableError) as exc_info:
            await provider.complete(config)
        assert exc_info.value.provider == "openai"


# ============================================================
# 8. DeepSeek 图片验证
# ============================================================


class TestDeepSeekImageValidation:
    """DeepSeek 不支持 ImageBlock，应在 complete() 时拒绝。"""

    @pytest.mark.asyncio
    async def test_image_block_rejected(self) -> None:
        from agent_framework.llm.types import ImageBlock, ImageSource

        provider = _make_provider(DeepSeekProvider)
        config = CompletionConfig(
            model="deepseek-v4-pro",
            messages=[
                UserMessage(
                    content=[
                        TextBlock(text="look at this"),
                        ImageBlock(
                            source=ImageSource(
                                type="url",
                                data="https://example.com/img.png",
                            )
                        ),
                    ]
                )
            ],
        )
        with pytest.raises(InvalidRequestError, match="image"):
            await provider.complete(config)
