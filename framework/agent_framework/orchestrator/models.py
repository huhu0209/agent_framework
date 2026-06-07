"""Orchestrator data models — Worker 注册、子任务拆分与执行结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from agent_framework.agents.base import Agent


@dataclass
class WorkerSpec:
    """Worker 注册信息：名称、描述、工厂函数。"""

    name: str
    description: str
    factory: Callable[..., Agent]


@dataclass
class SubTask:
    """分解后的子任务，含依赖关系。"""

    id: str
    worker: str
    prompt: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class SubTaskResult:
    """子任务执行结果。"""

    id: str
    worker: str
    output: str
    success: bool
    error: str | None = None
