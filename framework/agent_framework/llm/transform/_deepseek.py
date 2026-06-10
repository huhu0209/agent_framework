"""DeepSeek 格式转换。"""

from __future__ import annotations

import json

from ..types import (
    ContentBlock,
    Message,
    StopReason,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
)


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


def parse_deepseek_response(data: dict) -> tuple[list[ContentBlock], StopReason, UsageStats]:
    """解析 DeepSeek 响应（额外处理 reasoning_content）。"""
    from ._openai import parse_openai_response

    blocks, stop_reason, usage = parse_openai_response(data)

    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})

    reasoning = message.get("reasoning_content")
    if reasoning:
        blocks.append(ThinkingBlock(thinking=reasoning))

    return blocks, stop_reason, usage
