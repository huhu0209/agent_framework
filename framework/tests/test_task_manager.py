"""TaskManager 测试 — 持久化 DAG。"""

import json
import pytest

from agent_framework.tasks.manager import (
    MAX_ACTIVE_TASKS,
    TaskConflictError,
    TaskLimitError,
    TaskManager,
    TaskNotFoundError,
    TaskStatusError,
)
from agent_framework.tasks.types import TaskStatus


@pytest.fixture
def mgr(tmp_path):
    return TaskManager(tmp_path / "tasks")


# --- CRUD ---


def test_create_persists_json(mgr):
    task = mgr.create(subject="测试任务", description="详细描述")
    assert task.id == "1"
    assert task.subject == "测试任务"
    assert task.status == TaskStatus.PENDING
    assert task.created_at != ""


def test_create_auto_increments_id(mgr):
    t1 = mgr.create(subject="a")
    t2 = mgr.create(subject="b")
    assert int(t2.id) == int(t1.id) + 1


def test_create_over_limit(tmp_path):
    mgr = TaskManager(tmp_path / "tasks")
    for i in range(MAX_ACTIVE_TASKS):
        mgr.create(subject=f"task-{i}")
    with pytest.raises(TaskLimitError):
        mgr.create(subject="overflow")


def test_get_returns_task(mgr):
    created = mgr.create(subject="find me")
    found = mgr.get(created.id)
    assert found is not None
    assert found.subject == "find me"


def test_get_returns_none_for_missing(mgr):
    assert mgr.get("999") is None


# --- 状态转换 ---


def test_update_status_pending_to_in_progress(mgr):
    task = mgr.create(subject="do work")
    updated = mgr.update(task.id, status=TaskStatus.IN_PROGRESS)
    assert updated.status == TaskStatus.IN_PROGRESS


def test_update_status_invalid_transition(mgr):
    task = mgr.create(subject="done already")
    mgr.update(task.id, status=TaskStatus.IN_PROGRESS)
    mgr.update(task.id, status=TaskStatus.COMPLETED)
    with pytest.raises(TaskStatusError):
        mgr.update(task.id, status=TaskStatus.IN_PROGRESS)


def test_update_only_one_in_progress(mgr):
    t1 = mgr.create(subject="first")
    t2 = mgr.create(subject="second")
    mgr.update(t1.id, status=TaskStatus.IN_PROGRESS)
    with pytest.raises(TaskConflictError):
        mgr.update(t2.id, status=TaskStatus.IN_PROGRESS)


def test_update_nonexistent_raises(mgr):
    with pytest.raises(TaskNotFoundError):
        mgr.update("999", status=TaskStatus.IN_PROGRESS)


# --- 依赖 ---


def test_add_blocked_by_maintains_bidirectional(mgr):
    t1 = mgr.create(subject="A")
    t2 = mgr.create(subject="B")
    mgr.update(t2.id, add_blocked_by=[t1.id])

    t2_updated = mgr.get(t2.id)
    assert t1.id in t2_updated.blocked_by

    t1_updated = mgr.get(t1.id)
    assert t2.id in t1_updated.blocks


def test_complete_clears_downstream_dependency(mgr):
    t1 = mgr.create(subject="A")
    t2 = mgr.create(subject="B")
    mgr.update(t2.id, add_blocked_by=[t1.id])
    mgr.update(t1.id, status=TaskStatus.IN_PROGRESS)
    mgr.update(t1.id, status=TaskStatus.COMPLETED)

    t2_updated = mgr.get(t2.id)
    assert t1.id not in t2_updated.blocked_by


# --- list_all ---


def test_list_all_empty(mgr):
    assert mgr.list_all() == "(无任务)"


def test_list_all_shows_tasks(mgr):
    mgr.create(subject="待办")
    output = mgr.list_all()
    assert "待办" in output


# --- 损坏文件 ---


def test_corrupted_json_skipped(mgr):
    mgr.create(subject="good task")
    bad_path = mgr._dir / "task_99.json"
    bad_path.write_text("{broken json")
    tasks = mgr._load_all()
    assert len(tasks) == 1
    assert tasks[0].subject == "good task"
