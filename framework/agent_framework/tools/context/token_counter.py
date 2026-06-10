"""Token 估算 — 基于字符数的快速估算，避免额外 API 调用。"""

from __future__ import annotations

from agent_framework.llm.types import (
    CompletionConfig,
    Message,
    ProviderInfo,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UsageStats,
)

# 估算系数：4 字符 ≈ 1 token，乘 1.33 补偿非英语文本开销
_CHAR_TO_TOKEN_RATIO = 1.33 / 4


def _count_message_chars(msg: Message) -> int:
    """计算单条消息的字符数（不含 role 等元数据开销）。"""
    if isinstance(msg, SystemMessage):
        return len(msg.content)

    if isinstance(msg, ToolMessage):
        return len(msg.content)

    # UserMessage / AssistantMessage: 遍历 content blocks
    total = 0
    for block in msg.content:
        if isinstance(block, TextBlock):
            total += len(block.text)
        elif isinstance(block, ToolResultBlock):
            total += len(block.content)
        elif isinstance(block, ToolUseBlock):
            total += len(str(block.input))
    return total


def estimate_tokens(messages: list[Message]) -> int:
    """估算消息列表的 token 数。

    公式: sum(char_count / 4) * 1.33, 向上取整。
    空列表返回 0。
    """
    if not messages:
        return 0

    total_chars = sum(_count_message_chars(msg) for msg in messages)
    return int(total_chars * _CHAR_TO_TOKEN_RATIO)


def estimate_with_usage(new_messages: list[Message], last_usage: UsageStats) -> int:
    """混合估算：上次已知 token 用量 + 新消息的估算量。

    当 provider 返回了 usage 数据时，复用精确值，只估算增量部分。
    """
    return last_usage.input_tokens + estimate_tokens(new_messages)


def get_effective_window(adapter: object, config: CompletionConfig) -> int:
    """获取有效的上下文窗口大小（三级优先级）。

    Priority 1: config.max_context_tokens（调用方显式指定）
    Priority 2: adapter.get_max_context_tokens()（adapter 级别配置）
    Priority 3: adapter.get_provider_info().max_context_tokens（provider 默认值）
    """
    # Priority 1: config 显式覆盖
    if config.max_context_tokens is not None:
        return config.max_context_tokens

    # Priority 2: adapter 级别（如 ResilientLLMAdapter 包装时指定）
    get_max = getattr(adapter, "get_max_context_tokens", None)
    if callable(get_max):
        result = get_max()
        if result is not None:
            return result

    # Priority 3: provider 默认值
    get_info = getattr(adapter, "get_provider_info", None)
    if callable(get_info):
        info = get_info()
        if isinstance(info, ProviderInfo):
            return info.max_context_tokens

    # 不应该到这里 — provider 总是会返回 ProviderInfo
    raise ValueError(
        "Cannot determine effective context window: "
        "adapter has no get_max_context_tokens() or get_provider_info()"
    )
