"""Agent ABC + AgentEvent — 多类型 Agent 的统一接口契约和事件模型。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass
class AgentEvent:
    """Agent 执行过程中产生的事件基类。"""

    type: str
    step: int
    data: dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Agent 抽象基类，定义统一的 run() 接口。"""

    @abstractmethod
    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        yield  # pragma: no cover
