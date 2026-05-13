"""消息格式转换层。

纯函数集合，负责内部统一格式与各家 API 格式的互转。
所有函数无副作用，易于测试。

支持的目标格式：
- OpenAI ChatCompletions（DeepSeek / OpenAI 共用）
- Anthropic Messages（阶段 5 实现）
"""

from __future__ import annotations

import json
from typing import Any

from .types import (
    AssistantMessage,
    ContentBlock,
    ImageBlock,
    Message,
    StopReason,
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


# ============================================================
# 内部格式 → OpenAI/DeepSeek 格式
# ============================================================


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


def messages_to_deepseek(messages: list[Message]) -> list[dict]:
    """将内部统一消息转换为 DeepSeek/OpenAI 格式（含 reasoning_content）。

    与 messages_to_openai 的区别：
    - ThinkingBlock → reasoning_content 字段（非 OpenAI 标准）
    - tool call 场景必须保留 reasoning_content（否则 DeepSeek 400 错误）
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
            blocks = msg.content if isinstance(msg.content, list) else []
            text_parts: list[str] = []
            reasoning_parts: list[str] = []
            tool_calls: list[dict] = []
            tool_results: list[dict] = []

            for block in blocks:
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
                    })

            # tool_result → 独立 tool role 消息
            for tr in tool_results:
                result.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_use_id"],
                    "content": tr["content"],
                })

            if tool_calls:
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
                continue
            else:
                text = "\n".join(text_parts) if text_parts else ""
                entry = {"role": msg.role, "content": text}
                if reasoning_parts and msg.role == "assistant":
                    entry["reasoning_content"] = "\n".join(reasoning_parts)
                result.append(entry)

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


# ============================================================
# OpenAI/DeepSeek 响应 → 内部格式
# ============================================================


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
            args = {"_raw_arguments": args_str}

        content_blocks.append(ToolUseBlock(
            id=tc.get("id", ""),
            name=func.get("name", ""),
            input=args,
        ))

    stop_reason = _map_openai_stop_reason(choice.get("finish_reason", ""))
    usage = _parse_openai_usage(usage_data)

    return content_blocks, stop_reason, usage


def parse_deepseek_response(data: dict) -> tuple[list[ContentBlock], StopReason, UsageStats]:
    """解析 DeepSeek 响应（额外处理 reasoning_content）。"""
    blocks, stop_reason, usage = parse_openai_response(data)

    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})

    reasoning = message.get("reasoning_content")
    if reasoning:
        blocks.append(ThinkingBlock(thinking=reasoning))

    return blocks, stop_reason, usage


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


# ============================================================
# 工具定义转换
# ============================================================


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


# ============================================================
# 采样参数构建
# ============================================================


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
