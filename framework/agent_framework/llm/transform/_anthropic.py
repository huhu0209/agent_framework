"""Anthropic 格式转换。"""

from __future__ import annotations

from ..types import (
    ContentBlock,
    ImageBlock,
    Message,
    StopReason,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolDefinition,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
)


def messages_to_anthropic(messages: list[Message]) -> tuple[str, list[dict]]:
    """将内部统一消息转换为 Anthropic Messages API 格式。

    Anthropic 与 OpenAI 的关键差异：
    - system 是顶层字段，不在 messages 数组里
    - 必须以 user 消息开头，严格交替 user/assistant
    - tool_use 是 assistant content block，不是 tool_calls 数组
    - tool_result 是 user content block，不是独立 tool role
    - arguments 是 object，不是 JSON 字符串
    - thinking block 有 budget_tokens 控制

    Returns:
        (system_prompt, anthropic_messages) 元组
    """
    system_prompt = ""
    anthropic_messages: list[dict] = []
    pending_tool_results: list[dict] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            # Anthropic: 拼接所有 system 消息
            if system_prompt:
                system_prompt += "\n\n"
            system_prompt += msg.content

        elif isinstance(msg, ToolMessage):
            # 转换为 Anthropic tool_result content block
            pending_tool_results.append({
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id,
                "content": msg.content,
            })

        else:
            # 先 flush 积攒的 tool_results 为一条 user 消息
            if pending_tool_results:
                anthropic_messages.append({
                    "role": "user",
                    "content": pending_tool_results,
                })
                pending_tool_results = []

            blocks = msg.content if isinstance(msg.content, list) else []
            anthropic_blocks = _to_anthropic_blocks(blocks)

            if anthropic_blocks:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": anthropic_blocks,
                })

    # 最后 flush
    if pending_tool_results:
        anthropic_messages.append({
            "role": "user",
            "content": pending_tool_results,
        })

    # 确保 messages 不为空
    if not anthropic_messages:
        anthropic_messages.append({
            "role": "user",
            "content": [{"type": "text", "text": "."}],
        })

    # 确保以 user 开头
    if anthropic_messages[0]["role"] != "user":
        anthropic_messages.insert(0, {
            "role": "user",
            "content": [{"type": "text", "text": "."}],
        })

    return system_prompt, anthropic_messages


def _to_anthropic_blocks(blocks: list[ContentBlock]) -> list[dict]:
    """将 ContentBlock 列表转换为 Anthropic content block 格式。"""
    result: list[dict] = []

    for block in blocks:
        if isinstance(block, TextBlock):
            result.append({"type": "text", "text": block.text})

        elif isinstance(block, ImageBlock):
            result.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": block.source.media_type,
                    "data": block.source.data,
                },
            })

        elif isinstance(block, ToolUseBlock):
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,  # Anthropic 用 object，不需要 stringify
            })

        elif isinstance(block, ToolResultBlock):
            result.append({
                "type": "tool_result",
                "tool_use_id": block.tool_use_id,
                "content": block.content,
                "is_error": block.is_error,
            })

        elif isinstance(block, ThinkingBlock):
            result.append({
                "type": "thinking",
                "thinking": block.thinking,
            })
            if block.signature:
                result[-1]["signature"] = block.signature

    return result


def tools_to_anthropic(tools: list[ToolDefinition]) -> list[dict]:
    """将统一工具定义转换为 Anthropic tool 格式。"""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters.model_dump(exclude_none=True),
        }
        for t in tools
    ]


def parse_anthropic_response(data: dict) -> tuple[list[ContentBlock], StopReason, UsageStats]:
    """解析 Anthropic Messages API 响应。"""
    content_blocks: list[ContentBlock] = []

    for block in data.get("content", []):
        block_type = block.get("type")

        if block_type == "text":
            text = block.get("text", "")
            if text:
                content_blocks.append(TextBlock(text=text))

        elif block_type == "tool_use":
            content_blocks.append(ToolUseBlock(
                id=block.get("id", ""),
                name=block.get("name", ""),
                input=block.get("input", {}),
            ))

        elif block_type == "thinking":
            content_blocks.append(ThinkingBlock(
                thinking=block.get("thinking", ""),
                signature=block.get("signature"),
            ))

    # 停止原因
    stop_map = {
        "end_turn": StopReason.END_TURN,
        "max_tokens": StopReason.MAX_TOKENS,
        "tool_use": StopReason.TOOL_USE,
        "stop_sequence": StopReason.STOP_SEQUENCE,
    }
    stop_reason = stop_map.get(data.get("stop_reason", ""), StopReason.END_TURN)

    # usage
    usage_data = data.get("usage", {})
    usage = UsageStats(
        input_tokens=usage_data.get("input_tokens", 0),
        output_tokens=usage_data.get("output_tokens", 0),
        cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
        cache_write_tokens=usage_data.get("cache_creation_input_tokens", 0),
    )

    return content_blocks, stop_reason, usage
