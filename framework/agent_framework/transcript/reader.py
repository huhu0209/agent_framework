"""Transcript 读取器 — 从 JSONL 恢复对话。"""

import json
from pathlib import Path
from typing import Iterator

from agent_framework.llm.types import (
    AssistantMessage,
    Message,
    TextBlock,
    ToolMessage,
    ToolUseBlock,
    UserMessage,
)
from agent_framework.transcript.types import TranscriptEvent, TranscriptEventType


class TranscriptReader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def events(self) -> Iterator[TranscriptEvent]:
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                yield TranscriptEvent(
                    type=TranscriptEventType(data["type"]),
                    timestamp=data["timestamp"],
                    content=data["content"],
                    tool_call_id=data.get("tool_call_id"),
                    tool_name=data.get("tool_name"),
                )

    def to_messages(self) -> list[Message]:
        messages: list[Message] = []
        for ev in self.events():
            if ev.type == TranscriptEventType.USER:
                messages.append(UserMessage(content=[TextBlock(text=ev.content)]))
            elif ev.type == TranscriptEventType.ASSISTANT:
                blocks = _deserialize_content_blocks(ev.content)
                messages.append(AssistantMessage(content=blocks))
            elif ev.type == TranscriptEventType.TOOL_RESULT:
                messages.append(ToolMessage(
                    tool_call_id=ev.tool_call_id,
                    content=ev.content,
                ))
        return messages


def _deserialize_content_blocks(data: list[dict]) -> list:
    type_map = {
        "text": TextBlock,
        "tool_use": ToolUseBlock,
    }
    blocks = []
    for item in data:
        cls = type_map.get(item.get("type"))
        if cls is not None:
            blocks.append(cls.model_validate(item))
    return blocks
