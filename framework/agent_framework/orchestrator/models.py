"""Orchestrator data models — Worker 注册、子任务拆分与执行结果。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from agent_framework.agents.base import Agent

if TYPE_CHECKING:
    from agent_framework.llm.base import ILLMAdapter
    from agent_framework.tools.router import ToolRouter
    from agent_framework.tools.types import ToolUseContext


class WorkerFactory(Protocol):
    def __call__(
        self, *, adapter: ILLMAdapter, model: str, router: ToolRouter, ctx: ToolUseContext,
    ) -> Agent: ...


@dataclass(frozen=True)
class WorkerSpec:
    """Worker 注册信息：名称、描述、工厂函数。"""

    name: str
    description: str
    factory: WorkerFactory


@dataclass(frozen=True)
class SubTask:
    """分解后的子任务，含依赖关系。"""

    id: str
    worker: str
    prompt: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class SubTaskResult:
    """子任务执行结果。"""

    id: str
    worker: str
    output: str
    success: bool
    error: str | None = None
