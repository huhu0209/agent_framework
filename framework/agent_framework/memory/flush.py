"""Memory Flush — 压缩前从对话中提取关键事件并写入每日日志。"""

from __future__ import annotations

from datetime import datetime

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    SystemMessage,
    TextBlock,
    UserMessage,
)

_FLUSH_SYSTEM_PROMPT = """\
从以下对话中提取值得跨会话保留的关键事件。

只记录以下类型的事件：
- 决策：做出了什么选择，为什么
- 偏好：用户表达了什么倾向或纠正
- 错误：遇到了什么错误，怎么修复的
- 约定：设立了什么规范或工作流
- 进展：完成了什么有意义的步骤

每条事件格式：
## [HH:MM] 标签
简要描述 + 原因（如适用）+ 影响/后续

不记录：临时调试信息、问候语、纯信息查询、RAG 检索结果。
如果对话中没有值得记录的事件，输出 NO_EVENTS。

直接输出 Markdown 格式的事件列表，不要包装在代码块中。"""

_NO_EVENTS = "NO_EVENTS"


class FlushExtractor:
    """从对话中提取关键事件。"""

    def __init__(self, adapter: ILLMAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model

    async def extract(
        self,
        conversation_text: str,
        current_time: datetime,
    ) -> str | None:
        """调 LLM 提取关键事件。无事件返回 None。"""
        messages = [
            SystemMessage(content=_FLUSH_SYSTEM_PROMPT),
            UserMessage(content=[TextBlock(
                text=f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M')}\n\n对话：\n{conversation_text}",
            )]),
        ]

        config = CompletionConfig(
            model=self._model,
            messages=messages,
            tools=[],
            max_tokens=1000,
            temperature=0.3,
        )

        result: CompletionResult = await self._adapter.complete(config)

        for block in result.content:
            if isinstance(block, TextBlock):
                text = block.text.strip()
                if not text or text == _NO_EVENTS:
                    return None
                return text

        return None

    async def flush(
        self,
        conversation_text: str,
        current_time: datetime,
        log_manager,
    ) -> bool:
        """提取事件并追加到每日日志。有事件写入返回 True。"""
        events_text = await self.extract(conversation_text, current_time)
        if events_text is None:
            return False

        date_str = current_time.strftime("%Y-%m-%d")
        log_path = log_manager._log_path(date_str)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(events_text)

        return True
