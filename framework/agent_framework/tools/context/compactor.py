"""上下文自动压缩 — 当 token 估算接近窗口阈值时，将旧消息摘要压缩。"""

from __future__ import annotations

from dataclasses import dataclass

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.transform import normalize_messages
from agent_framework.llm.types import (
    AssistantMessage,
    CompletionConfig,
    CompletionResult,
    Message,
    SystemMessage,
    TextBlock,
    ToolMessage,
    UserMessage,
)


@dataclass
class CompactConfig:
    """压缩配置。"""

    keep_turns: int = 20
    trigger_pct: float = 0.75
    target_pct: float = 0.50
    max_summary_tokens: int = 8000


_SUMMARY_SYSTEM_PROMPT = """\
你是一个对话摘要助手。你需要将一段较长的对话历史压缩为简洁的结构化摘要。

CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.

请按以下 7 个部分组织摘要：

## 已完成工作
列出对话中已经完成的任务和步骤。

## 当前状态
描述当前进展到哪一步，正在做什么。

## 关键文件
列出涉及的重要文件路径及其作用。

## 关键决策
记录对话中做出的重要技术决策及其理由。

## 错误与修复
记录遇到的错误和对应的修复方法。

## 待办任务
列出尚未完成的任务。

## 重要上下文
其他需要保留的关键信息（变量值、配置、约束条件等）。
"""


def should_compact(estimated: int, window: int, config: CompactConfig) -> bool:
    """判断是否需要压缩上下文。"""
    threshold = min(int(window * config.trigger_pct), window - 8000)
    return estimated > threshold


def _group_by_user_turns(
    messages: list[Message],
) -> tuple[list[Message], list[list[Message]]]:
    """将消息按 UserMessage 边界分组。

    Returns:
        (system_prefix, turn_groups)
        - system_prefix: 开头的 SystemMessage 列表
        - turn_groups: 每个 group 以 UserMessage 开始，后续跟随对应的
          AssistantMessage / ToolMessage 直到下一个 UserMessage
    """
    system_prefix: list[Message] = []
    turn_groups: list[list[Message]] = []

    # 提取开头的 SystemMessage
    idx = 0
    while idx < len(messages) and isinstance(messages[idx], SystemMessage):
        system_prefix.append(messages[idx])
        idx += 1

    # 按用户轮次分组
    current_group: list[Message] = []
    for msg in messages[idx:]:
        if isinstance(msg, UserMessage):
            if current_group:
                turn_groups.append(current_group)
            current_group = [msg]
        else:
            current_group.append(msg)

    if current_group:
        turn_groups.append(current_group)

    return system_prefix, turn_groups


def _serialize_for_summary(messages: list[Message]) -> str:
    """将消息列表序列化为文本，供摘要 LLM 使用。"""
    parts: list[str] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            parts.append(f"[System] {msg.content}")
        elif isinstance(msg, UserMessage):
            text = " ".join(
                block.text for block in msg.content if isinstance(block, TextBlock)
            )
            parts.append(f"[User] {text}")
        elif isinstance(msg, AssistantMessage):
            text = " ".join(
                block.text for block in msg.content if isinstance(block, TextBlock)
            )
            parts.append(f"[Assistant] {text}")
        elif isinstance(msg, ToolMessage):
            parts.append(f"[Tool:{msg.tool_call_id}] {msg.content[:500]}")

    return "\n\n".join(parts)


async def _generate_summary(
    adapter: ILLMAdapter,
    model: str,
    old_messages: list[Message],
    config: CompactConfig,
) -> str:
    """调用 LLM 生成旧消息的摘要。"""
    serialized = _serialize_for_summary(old_messages)

    summary_messages: list[Message] = [
        SystemMessage(content=_SUMMARY_SYSTEM_PROMPT),
        UserMessage(content=[TextBlock(text=f"请摘要以下对话：\n\n{serialized}")]),
    ]

    call_config = CompletionConfig(
        model=model,
        messages=summary_messages,
        tools=[],
        max_tokens=config.max_summary_tokens,
        temperature=0.3,
    )

    result: CompletionResult = await adapter.complete(call_config)

    # 从结果中提取 TextBlock
    for block in result.content:
        if isinstance(block, TextBlock):
            return block.text

    # 兜底：如果没有 TextBlock，返回空字符串
    return ""


async def compact(
    messages: list[Message],
    adapter: ILLMAdapter,
    model: str,
    config: CompactConfig,
    step: int,
) -> list[Message]:
    """执行上下文压缩。

    1. 按用户轮次分组
    2. 保留最近的 keep_turns 轮
    3. 将旧轮次压缩为摘要
    4. 重新组装消息列表
    """
    system_prefix, turn_groups = _group_by_user_turns(messages)

    # 不需要压缩
    if len(turn_groups) <= config.keep_turns:
        return messages

    # 分割：旧轮次 vs 近期轮次
    split_point = len(turn_groups) - config.keep_turns
    old_groups = turn_groups[:split_point]
    recent_groups = turn_groups[split_point:]

    # 展平旧消息并生成摘要
    old_flat = [msg for group in old_groups for msg in group]
    summary_text = await _generate_summary(adapter, model, old_flat, config)

    # 构建边界标记
    boundary = (
        f"\n\n[上下文压缩于 step {step}，"
        f"之前 {len(old_flat)} 条消息被摘要替代。"
        f"如需原文，可读取完整对话记录]"
    )

    # 创建摘要 UserMessage
    summary_msg = UserMessage(
        content=[TextBlock(text=summary_text + boundary)],
    )

    # 重新组装：system_prefix + summary + recent turns
    recent_flat = [msg for group in recent_groups for msg in group]
    result = [*system_prefix, summary_msg, *recent_flat]

    return normalize_messages(result)
