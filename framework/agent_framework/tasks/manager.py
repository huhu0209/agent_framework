"""TaskManager — 持久化任务 DAG。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from agent_framework.tasks.types import Task, TaskStatus

logger = logging.getLogger(__name__)

MAX_ACTIVE_TASKS = 12


class TaskManager:
    """每个 task 一个 JSON 文件，存储在指定目录下。"""

    def __init__(self, tasks_dir: Path):
        self._dir = tasks_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._next_id = self._load_max_id() + 1

    # ---- CRUD ----

    def create(self, subject: str, description: str = "") -> Task:
        active = self._count_active()
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

    def update(self, task_id: str, **changes) -> Task:
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

    def list_all(self) -> str:
        tasks = self._load_all()
        if not tasks:
            return "(无任务)"

        status_mark = {
            TaskStatus.PENDING: " ",
            TaskStatus.IN_PROGRESS: ">",
            TaskStatus.COMPLETED: "x",
            TaskStatus.FAILED: "!",
            TaskStatus.CANCELLED: "-",
            TaskStatus.DELETED: "d",
        }
        lines = []
        for t in sorted(tasks, key=lambda t: int(t.id)):
            mark = status_mark.get(t.status, "?")
            deps = f" (等待: {', '.join(t.blocked_by)})" if t.blocked_by else ""
            lines.append(f"  [{mark}] {t.id}. {t.subject}{deps}")
        return "\n".join(lines)

    # ---- 内部 ----

    def _path(self, task_id: str) -> Path:
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

    def _count_active(self) -> int:
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

    def _apply_changes(self, task: Task, changes: dict) -> Task:
        kwargs = {
            "id": task.id,
            "subject": changes.get("subject", task.subject),
            "description": changes.get("description", task.description),
            "status": TaskStatus(changes["status"]) if "status" in changes else task.status,
            "owner": changes.get("owner", task.owner),
            "blocked_by": task.blocked_by.copy(),
            "blocks": task.blocks.copy(),
            "created_at": task.created_at,
            "updated_at": self._now(),
        }

        for dep_id in changes.get("add_blocked_by", []):
            if dep_id not in kwargs["blocked_by"]:
                kwargs["blocked_by"].append(dep_id)
            dep_task = self.get(dep_id)
            if dep_task and task.id not in dep_task.blocks:
                self._write(Task(
                    id=dep_task.id, subject=dep_task.subject,
                    description=dep_task.description, status=dep_task.status,
                    owner=dep_task.owner,
                    blocked_by=dep_task.blocked_by,
                    blocks=dep_task.blocks + [task.id],
                    created_at=dep_task.created_at, updated_at=self._now(),
                ))

        for dep_id in changes.get("add_blocks", []):
            if dep_id not in kwargs["blocks"]:
                kwargs["blocks"].append(dep_id)
            dep_task = self.get(dep_id)
            if dep_task and task.id not in dep_task.blocked_by:
                self._write(Task(
                    id=dep_task.id, subject=dep_task.subject,
                    description=dep_task.description, status=dep_task.status,
                    owner=dep_task.owner,
                    blocked_by=dep_task.blocked_by + [task.id],
                    blocks=dep_task.blocks,
                    created_at=dep_task.created_at, updated_at=self._now(),
                ))

        return Task(**kwargs)

    def _clear_dependency(self, completed_id: str):
        for task in self._load_all():
            if completed_id in task.blocked_by:
                new_blocked = [x for x in task.blocked_by if x != completed_id]
                self._write(Task(
                    id=task.id, subject=task.subject,
                    description=task.description, status=task.status,
                    owner=task.owner,
                    blocked_by=new_blocked,
                    blocks=task.blocks,
                    created_at=task.created_at, updated_at=self._now(),
                ))


class TaskLimitError(Exception): ...
class TaskNotFoundError(Exception): ...
class TaskConflictError(Exception): ...
class TaskStatusError(Exception): ...
