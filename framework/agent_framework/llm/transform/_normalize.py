"""消息规范化。"""

from __future__ import annotations

from ..types import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolMessage,
    ToolUseBlock,
    UserMessage,
)


def normalize_messages(messages: list[Message]) -> list[Message]:
    """发送前的消息规范化。

    三条硬性约束：
    1. 每个 tool_use 有匹配的 tool_result（缺失补 "(cancelled)"）
    2. user / assistant 严格交替（连续同角色合并）
    3. 保留协议字段（当前内部格式无额外元数据，此条为预留）
    """
    if not messages:
        return []

    result: list[Message] = []

    for msg in messages:
        if not result:
            if isinstance(msg, (UserMessage, AssistantMessage)):
                result.append(msg.model_copy(update={"content": list(msg.content)}))
            else:
                result.append(msg)
            continue

        last = result[-1]

        # SystemMessage / ToolMessage 不合并
        if isinstance(msg, (SystemMessage, ToolMessage)):
            result.append(msg)
            continue

        # 同角色合并（UserMessage + UserMessage / AssistantMessage + AssistantMessage）
        if type(msg) is type(last) and isinstance(msg, (UserMessage, AssistantMessage)):
            last.content = [*last.content, *msg.content]
            continue

        if isinstance(msg, (UserMessage, AssistantMessage)):
            result.append(msg.model_copy(update={"content": list(msg.content)}))
        else:
            result.append(msg)

    result = _pair_tool_results(result)
    return result


def _pair_tool_results(messages: list[Message]) -> list[Message]:
    """确保每个 tool_use 都有对应的 ToolMessage。

    扫描所有 AssistantMessage 中的 ToolUseBlock，收集其 id，
    与现有 ToolMessage 的 tool_call_id 对比，缺失的补 "(cancelled)" 占位。
    """
    tool_use_ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    tool_use_ids.add(block.id)

    if not tool_use_ids:
        return messages

    result_ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, ToolMessage):
            result_ids.add(msg.tool_call_id)

    missing = tool_use_ids - result_ids
    if not missing:
        return messages

    placeholders = [
        ToolMessage(tool_call_id=uid, content="(cancelled)")
        for uid in sorted(missing)
    ]

    # 找到最后一个 ToolMessage 的位置，在其后插入
    insert_idx = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            insert_idx = i

    if insert_idx == -1:
        # 没有 ToolMessage，找到最后一个 AssistantMessage 的位置
        for i, msg in enumerate(messages):
            if isinstance(msg, AssistantMessage):
                insert_idx = i

    new_messages = list(messages)
    for j, placeholder in enumerate(placeholders):
        new_messages.insert(insert_idx + 1 + j, placeholder)

    return new_messages
