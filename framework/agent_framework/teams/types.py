"""Teams 核心类型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TeammateStatus(str, Enum):
    WORKING = "working"
    IDLE = "idle"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class TeammateConfig:
    name: str
    role: str
    system_prompt: str
    allowed_tools: list[str] | None = None
    model: str | None = None
    max_idle_seconds: int = 60


@dataclass(frozen=True)
class TeamMessage:
    type: str  # message | broadcast | shutdown_request
    from_: str
    to: str
    content: str
    timestamp: float


@dataclass(frozen=True)
class TeamNotification:
    name: str
    status: str
