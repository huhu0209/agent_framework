"""Task 数据模型测试。"""

from agent_framework.tasks.types import Task, TaskStatus, RuntimeTask, RuntimeTaskStatus


def test_task_is_frozen():
    task = Task(id="1", subject="test")
    try:
        task.subject = "changed"
        assert False, "应该抛 FrozenInstanceError"
    except AttributeError:
        pass


def test_task_default_values():
    task = Task(id="1", subject="test")
    assert task.status == TaskStatus.PENDING
    assert task.description == ""
    assert task.owner == ""
    assert task.blocked_by == []
    assert task.blocks == []


def test_task_status_values():
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.IN_PROGRESS.value == "in_progress"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"
    assert TaskStatus.DELETED.value == "deleted"


def test_runtime_task_default():
    rt = RuntimeTask(task_id="1", prompt="hello")
    assert rt.status == RuntimeTaskStatus.RUNNING
    assert rt.output == ""
    assert rt.error == ""


def test_runtime_task_is_mutable():
    rt = RuntimeTask(task_id="1", prompt="hello")
    rt.status = RuntimeTaskStatus.COMPLETED
    rt.output = "done"
    assert rt.status == RuntimeTaskStatus.COMPLETED
    assert rt.output == "done"
