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


async def test_create_persists_json(mgr):
    task = await mgr.create(subject="测试任务", description="详细描述")
    assert task.id == "1"
    assert task.subject == "测试任务"
    assert task.status == TaskStatus.PENDING
    assert task.created_at != ""


async def test_create_auto_increments_id(mgr):
    t1 = await mgr.create(subject="a")
    t2 = await mgr.create(subject="b")
    assert int(t2.id) == int(t1.id) + 1


async def test_create_over_limit(tmp_path):
    mgr = TaskManager(tmp_path / "tasks")
    for i in range(MAX_ACTIVE_TASKS):
        await mgr.create(subject=f"task-{i}")
    with pytest.raises(TaskLimitError):
        await mgr.create(subject="overflow")


async def test_get_returns_task(mgr):
    created = await mgr.create(subject="find me")
    found = mgr.get(created.id)
    assert found is not None
    assert found.subject == "find me"


def test_get_returns_none_for_missing(mgr):
    assert mgr.get("999") is None


# --- 状态转换 ---


async def test_update_status_pending_to_in_progress(mgr):
    task = await mgr.create(subject="do work")
    updated = await mgr.update(task.id, status=TaskStatus.IN_PROGRESS)
    assert updated.status == TaskStatus.IN_PROGRESS


async def test_update_status_invalid_transition(mgr):
    task = await mgr.create(subject="done already")
    await mgr.update(task.id, status=TaskStatus.IN_PROGRESS)
    await mgr.update(task.id, status=TaskStatus.COMPLETED)
    with pytest.raises(TaskStatusError):
        await mgr.update(task.id, status=TaskStatus.IN_PROGRESS)


async def test_update_only_one_in_progress(mgr):
    t1 = await mgr.create(subject="first")
    t2 = await mgr.create(subject="second")
    await mgr.update(t1.id, status=TaskStatus.IN_PROGRESS)
    with pytest.raises(TaskConflictError):
        await mgr.update(t2.id, status=TaskStatus.IN_PROGRESS)


async def test_update_nonexistent_raises(mgr):
    with pytest.raises(TaskNotFoundError):
        await mgr.update("999", status=TaskStatus.IN_PROGRESS)


# --- 依赖 ---


async def test_add_blocked_by_maintains_bidirectional(mgr):
    t1 = await mgr.create(subject="A")
    t2 = await mgr.create(subject="B")
    await mgr.update(t2.id, add_blocked_by=[t1.id])

    t2_updated = mgr.get(t2.id)
    assert t1.id in t2_updated.blocked_by

    t1_updated = mgr.get(t1.id)
    assert t2.id in t1_updated.blocks


async def test_complete_clears_downstream_dependency(mgr):
    t1 = await mgr.create(subject="A")
    t2 = await mgr.create(subject="B")
    await mgr.update(t2.id, add_blocked_by=[t1.id])
    await mgr.update(t1.id, status=TaskStatus.IN_PROGRESS)
    await mgr.update(t1.id, status=TaskStatus.COMPLETED)

    t2_updated = mgr.get(t2.id)
    assert t1.id not in t2_updated.blocked_by


# --- list_all ---


def test_list_all_empty(mgr):
    assert mgr.list_all() == []


async def test_list_all_shows_tasks(mgr):
    await mgr.create(subject="待办")
    tasks = mgr.list_all()
    assert len(tasks) == 1
    assert tasks[0].subject == "待办"


# --- 损坏文件 ---


async def test_corrupted_json_skipped(mgr):
    await mgr.create(subject="good task")
    bad_path = mgr._dir / "task_99.json"
    bad_path.write_text("{broken json")
    tasks = mgr._load_all()
    assert len(tasks) == 1
    assert tasks[0].subject == "good task"


# --- 路径遍历防御 ---


def test_path_traversal_rejected(mgr):
    """task_id 含非数字字符时拒绝访问。"""
    with pytest.raises(TaskNotFoundError):
        mgr.get("../../etc/passwd")


async def test_update_rejects_non_numeric_id(mgr):
    with pytest.raises(TaskNotFoundError):
        await mgr.update("../secret", status=TaskStatus.IN_PROGRESS)


async def test_update_rejects_unknown_fields(mgr):
    task = await mgr.create(subject="test")
    with pytest.raises(TypeError, match="未知的更新字段"):
        await mgr.update(task.id, nonexistent_field="oops")
