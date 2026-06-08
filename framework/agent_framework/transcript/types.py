"""Transcript 事件类型定义。"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TranscriptEventType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"


@dataclass
class TranscriptEvent:
    type: TranscriptEventType
    timestamp: float
    content: str | list[dict[str, Any]] = ""
    tool_call_id: str | None = None
    tool_name: str | None = None
