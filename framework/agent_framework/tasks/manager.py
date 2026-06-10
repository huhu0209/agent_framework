"""TaskManager — 持久化任务 DAG。"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from agent_framework.tasks.types import Task, TaskStatus


class TaskChanges(TypedDict, total=False):
    subject: str
    description: str
    owner: str
    status: str
    add_blocked_by: list[str]
    add_blocks: list[str]

logger = logging.getLogger(__name__)

MAX_ACTIVE_TASKS = 12


class TaskManager:
    """每个 task 一个 JSON 文件，存储在指定目录下。

    注意：此类非线程安全，仅适用于 asyncio 单线程环境。
    """

    def __init__(self, tasks_dir: Path):
        self._dir = tasks_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._next_id = self._load_max_id() + 1
        self._lock = asyncio.Lock()

    # ---- CRUD ----

    _VALID_CHANGE_KEYS = frozenset({
        "subject", "description", "owner", "status",
        "add_blocked_by", "add_blocks",
    })

    async def create(self, subject: str, description: str = "") -> Task:
        async with self._lock:
            active = self.count_active()
            if active >= MAX_ACTIVE_TASKS:
                raise TaskLimitError(f"活跃任务已达上限 {MAX_ACTIVE_TASKS}")

            now = self._now()
            task = Task(
                id=str(self._next_id),
                subject=subject,
                description=description,
                created_at=now,
                updated_at=now,
            )
            self._next_id += 1
            self._write(task)
            return task

    def get(self, task_id: str) -> Task | None:
        path = self._path(task_id)
        if not path.exists():
            return None
        return self._read(path)

    async def update(self, task_id: str, **changes) -> Task:
        async with self._lock:
            invalid = set(changes) - self._VALID_CHANGE_KEYS
            if invalid:
                raise TypeError(f"未知的更新字段: {invalid}")

            task = self.get(task_id)
            if task is None:
                raise TaskNotFoundError(f"任务 {task_id} 不存在")

            new_status = changes.get("status")
            if new_status is not None:
                self._validate_transition(task.status, TaskStatus(new_status))

            if new_status == TaskStatus.IN_PROGRESS:
                if self._find_in_progress():
                    raise TaskConflictError("已有任务正在执行中")

            updated = self._apply_changes(task, changes)

            if updated.status == TaskStatus.COMPLETED:
                self._clear_dependency(updated.id)

            self._write(updated)
            return updated

    def list_all(self) -> list[Task]:
        return sorted(self._load_all(), key=lambda t: int(t.id))

    # ---- 内部 ----

    def _path(self, task_id: str) -> Path:
        if not task_id.isdigit():
            raise TaskNotFoundError(f"无效任务 ID: {task_id}")
        return self._dir / f"task_{task_id}.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _write(self, task: Task):
        data = {
            "id": task.id,
            "subject": task.subject,
            "description": task.description,
            "status": task.status.value,
            "owner": task.owner,
            "blockedBy": task.blocked_by,
            "blocks": task.blocks,
            "created_at": task.created_at or self._now(),
            "updated_at": self._now(),
        }
        self._path(task.id).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _read(self, path: Path) -> Task:
        data = json.loads(path.read_text())
        return Task(
            id=data["id"],
            subject=data["subject"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            owner=data.get("owner", ""),
            blocked_by=data.get("blockedBy", []),
            blocks=data.get("blocks", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def _load_all(self) -> list[Task]:
        tasks = []
        for path in sorted(self._dir.glob("task_*.json")):
            try:
                tasks.append(self._read(path))
            except Exception:
                logger.warning("无法读取任务文件 %s，跳过", path)
        return tasks

    def _load_max_id(self) -> int:
        max_id = 0
        for path in self._dir.glob("task_*.json"):
            try:
                tid = int(path.stem.split("_", 1)[1])
                max_id = max(max_id, tid)
            except (ValueError, IndexError):
                pass
        return max_id

    def count_active(self) -> int:
        return sum(
            1 for t in self._load_all()
            if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        )

    def _find_in_progress(self) -> Task | None:
        for t in self._load_all():
            if t.status == TaskStatus.IN_PROGRESS:
                return t
        return None

    def _validate_transition(self, old: TaskStatus, new: TaskStatus):
        allowed = {
            TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.DELETED},
            TaskStatus.IN_PROGRESS: {
                TaskStatus.COMPLETED, TaskStatus.FAILED,
                TaskStatus.CANCELLED, TaskStatus.PENDING,
            },
            TaskStatus.COMPLETED: set(),
            TaskStatus.FAILED: set(),
            TaskStatus.CANCELLED: set(),
            TaskStatus.DELETED: set(),
        }
        if new not in allowed.get(old, set()):
            raise TaskStatusError(f"不允许从 {old.value} 转换到 {new.value}")

    def _update_dependencies(
        self,
        task: Task,
        changes: dict,
    ) -> tuple[list[str], list[str], list[Task]]:
        """Handle blocked_by and blocks dependency updates.

        Returns (new_blocked_by, new_blocks, pending_writes).
        """
        new_blocked_by = list(task.blocked_by)
        new_blocks = list(task.blocks)
        pending_writes: list[Task] = []

        for dep_id in changes.get("add_blocked_by", []):
            if dep_id not in new_blocked_by:
                new_blocked_by.append(dep_id)
            dep_task = self.get(dep_id)
            if dep_task and task.id not in dep_task.blocks:
                pending_writes.append(dataclasses.replace(
                    dep_task,
                    blocks=dep_task.blocks + [task.id],
                    updated_at=self._now(),
                ))

        for dep_id in changes.get("add_blocks", []):
            if dep_id not in new_blocks:
                new_blocks.append(dep_id)
            dep_task = self.get(dep_id)
            if dep_task and task.id not in dep_task.blocked_by:
                pending_writes.append(dataclasses.replace(
                    dep_task,
                    blocked_by=dep_task.blocked_by + [task.id],
                    updated_at=self._now(),
                ))

        return new_blocked_by, new_blocks, pending_writes

    def _apply_changes(self, task: Task, changes: dict) -> Task:
        field_updates: dict = {"updated_at": self._now()}

        for key in ("subject", "description", "owner"):
            if key in changes:
                field_updates[key] = changes[key]

        if "status" in changes:
            field_updates["status"] = TaskStatus(changes["status"])

        updated = dataclasses.replace(task, **field_updates)

        new_blocked_by, new_blocks, pending_writes = self._update_dependencies(updated, changes)

        for dep_task in pending_writes:
            self._write(dep_task)

        return dataclasses.replace(updated, blocked_by=new_blocked_by, blocks=new_blocks)

    def _clear_dependency(self, completed_id: str):
        pending_clears: list[Task] = []
        for task in self._load_all():
            if completed_id in task.blocked_by:
                new_blocked = [x for x in task.blocked_by if x != completed_id]
                pending_clears.append(dataclasses.replace(
                    task,
                    blocked_by=new_blocked,
                    updated_at=self._now(),
                ))
        for dep_task in pending_clears:
            try:
                self._write(dep_task)
            except Exception as e:
                logger.warning("无法清理任务 %s 的依赖关系: %s", dep_task.id, e)


class TaskLimitError(Exception): ...
class TaskNotFoundError(Exception): ...
class TaskConflictError(Exception): ...
class TaskStatusError(Exception): ...
