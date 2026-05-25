"""语义记忆提取器 — 从对话或事件中提取长期记忆候选。"""

from __future__ import annotations

import json
import logging

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from agent_framework.memory.types import MemoryType, SemanticMemoryDraft

logger = logging.getLogger(__name__)

_PROMPT_BODY = """\
只提取以下类型：
- user: 用户偏好、工作风格、知识背景
- feedback: 值得记住的纠错、最佳实践（必须包含 **Why:** 和 **How to apply:**）
- project: 项目约束、截止日期、利益相关方信息（必须包含 **Why:** 和 **How to apply:**）
- reference: 外部系统、文档、资源的指针

不提取：一次性决策、临时调试信息、已在代码中体现的信息。

返回 JSON 数组，每个元素格式：
{"name": "简短名称", "description": "一句话描述(≤150字)", "type": "user|feedback|project|reference", "body": "Markdown 正文"}

feedback 和 project 类型的 body 必须包含：
**Why:** [这条规则为什么存在]
**How to apply:** [在什么场景下触发]

如果没有值得提取的内容，返回空数组 []。
只返回 JSON，不要其他内容。"""

_EVENTS_INTRO = "从以下已分类的事件中提取值得长期保留的语义记忆。"
_MESSAGES_INTRO = "从以下对话中提取值得跨会话长期保留的语义记忆。"


class SemanticExtractor:
    """从对话或事件中提取语义记忆候选。"""

    def __init__(self, adapter: ILLMAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model

    async def extract_from_events(
        self,
        events: list[tuple[str, str]],
    ) -> list[SemanticMemoryDraft]:
        """Flush 后级联：从已结构化的事件中提取。"""
        events_text = "\n".join(
            f"- [{etype}] {content}" for etype, content in events
        )
        return await self._call_llm(f"{_EVENTS_INTRO}\n\n{_PROMPT_BODY}", events_text)

    async def extract_from_messages(
        self,
        conversation_text: str,
    ) -> list[SemanticMemoryDraft]:
        """对话结束时：从对话文本中提取。"""
        return await self._call_llm(f"{_MESSAGES_INTRO}\n\n{_PROMPT_BODY}", conversation_text)

    async def _call_llm(
        self, system_prompt: str, input_text: str,
    ) -> list[SemanticMemoryDraft]:
        messages = [
            SystemMessage(content=system_prompt),
            UserMessage(content=[TextBlock(text=input_text)]),
        ]

        config = CompletionConfig(
            model=self._model,
            messages=messages,
            tools=[],
            max_tokens=1000,
            temperature=0.3,
        )

        result: CompletionResult = await self._adapter.complete(config)

        text = ""
        for block in result.content:
            if isinstance(block, TextBlock):
                text = block.text.strip()
                break

        if not text:
            return []

        try:
            items = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM 返回非法 JSON，跳过提取: %s", text[:200])
            return []

        if not isinstance(items, list):
            return []

        drafts: list[SemanticMemoryDraft] = []
        for item in items:
            try:
                drafts.append(SemanticMemoryDraft(
                    name=item["name"],
                    description=item["description"],
                    type=MemoryType(item["type"]),
                    body=item["body"],
                ))
            except (KeyError, ValueError) as e:
                logger.warning("跳过格式不完整的记忆候选: %s (%s)", item, e)
                continue

        return drafts
