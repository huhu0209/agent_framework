"""Task 系统 — 数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DELETED = "deleted"


@dataclass(frozen=True)
class Task:
    """持久化任务。"""
    id: str
    subject: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    owner: str = ""
    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class RuntimeTaskStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class RuntimeTask:
    """后台运行中的任务（非持久化，仅内存）。"""
    task_id: str
    prompt: str
    status: RuntimeTaskStatus = RuntimeTaskStatus.RUNNING
    output: str = ""
    error: str = ""
