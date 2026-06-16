"""OpenAI 格式转换。"""

from __future__ import annotations

import json
from typing import Any

from ..types import (
    CompletionConfig,
    ContentBlock,
    Message,
    StopReason,
    SystemMessage,
    TextBlock,
    ToolDefinition,
    ToolMessage,
    ToolUseBlock,
    UsageStats,
)


def messages_to_openai(messages: list[Message]) -> list[dict]:
    """将内部统一消息转换为 OpenAI ChatCompletions 格式。

    转换规则：
    - SystemMessage → {role: "system", content: string}
    - UserMessage → {role: "user", content: string | parts}
    - AssistantMessage → {role: "assistant", content: string, tool_calls?: [...]}
    - ToolMessage → {role: "tool", tool_call_id: string, content: string}
    - ToolUseBlock → tool_calls[].function.arguments (JSON.stringify)
    - ThinkingBlock → 丢弃（OpenAI 不支持回传思考过程）

    注意：DeepSeek 版本需要额外处理 reasoning_content，
    由 messages_to_deepseek() 函数处理。
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

        else:
            # UserMessage or AssistantMessage
            blocks = msg.content if isinstance(msg.content, list) else []
            text_parts, tool_calls = _extract_openai_blocks(blocks)

            if tool_calls:
                result.append({
                    "role": msg.role,
                    "content": " ".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls,
                })
            else:
                result.append({
                    "role": msg.role,
                    "content": "\n".join(text_parts) if text_parts else "",
                })

    return result


def _extract_openai_blocks(
    blocks: list[ContentBlock],
) -> tuple[list[str], list[dict]]:
    """从 ContentBlock 列表中提取文本和 tool_calls。

    Returns:
        (text_parts, tool_calls) 元组
    """
    text_parts: list[str] = []
    tool_calls: list[dict] = []

    for block in blocks:
        if isinstance(block, TextBlock):
            text_parts.append(block.text)
        elif isinstance(block, ToolUseBlock):
            tool_calls.append({
                "id": block.id,
                "type": "function",
                "function": {
                    "name": block.name,
                    "arguments": json.dumps(block.input, ensure_ascii=False),
                },
            })
        # ThinkingBlock / ImageBlock / ToolResultBlock 在 OpenAI 格式中不处理

    return text_parts, tool_calls


def parse_openai_response(data: dict) -> tuple[list[ContentBlock], StopReason, UsageStats]:
    """解析 OpenAI ChatCompletions 响应的核心字段。

    Returns:
        (content_blocks, stop_reason, usage) 元组
    """
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage_data = data.get("usage", {})

    content_blocks: list[ContentBlock] = []

    text = message.get("content")
    if text:
        content_blocks.append(TextBlock(text=text))

    for tc in message.get("tool_calls", []):
        func = tc.get("function", {})
        args_str = func.get("arguments", "{}")
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {"_raw": args_str}

        content_blocks.append(ToolUseBlock(
            id=tc.get("id", ""),
            name=func.get("name", ""),
            input=args,
        ))

    stop_reason = _map_openai_stop_reason(choice.get("finish_reason", ""))
    usage = _parse_openai_usage(usage_data)

    return content_blocks, stop_reason, usage


def _map_openai_stop_reason(finish_reason: str) -> StopReason:
    """映射 OpenAI finish_reason 到统一 StopReason。"""
    mapping = {
        "stop": StopReason.END_TURN,
        "length": StopReason.MAX_TOKENS,
        "tool_calls": StopReason.TOOL_USE,
        "content_filter": StopReason.END_TURN,
    }
    return mapping.get(finish_reason, StopReason.END_TURN)


def _parse_openai_usage(data: dict) -> UsageStats:
    """解析 OpenAI 格式的 usage 字段。"""
    return UsageStats(
        input_tokens=data.get("prompt_tokens", 0),
        output_tokens=data.get("completion_tokens", 0),
        cache_read_tokens=data.get("prompt_tokens_details", {}).get("cached_tokens", 0),
    )


def tools_to_openai(tools: list[ToolDefinition]) -> list[dict]:
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


def build_openai_sampling_params(config: CompletionConfig) -> dict:
    """从 CompletionConfig 提取 OpenAI 兼容的采样参数。

    不包含 model、messages、tools、stream——这些由 provider 自行构建。
    """
    params: dict[str, Any] = {}

    if config.temperature is not None:
        params["temperature"] = config.temperature
    if config.max_tokens is not None:
        params["max_tokens"] = config.max_tokens
    if config.top_p is not None:
        params["top_p"] = config.top_p
    if config.stop:
        params["stop"] = config.stop

    return params
