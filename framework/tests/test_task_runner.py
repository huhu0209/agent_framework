"""TaskRunner 测试 — 后台异步执行。"""

import asyncio
import pytest

from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.tasks.manager import TaskManager
from agent_framework.tasks.runner import TaskRunner
from agent_framework.tasks.types import RuntimeTaskStatus, TaskStatus
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


class FakeAdapter:
    """返回 END_TURN 的假 adapter。"""

    def __init__(self, text: str = "任务完成"):
        self._text = text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="fake",
            model=config.model,
            content=[TextBlock(text=self._text)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=10, output_tokens=5),
        )

    def get_max_context_tokens(self) -> int:
        return 128000


@pytest.fixture
def task_mgr(tmp_path):
    return TaskManager(tmp_path / "tasks")


@pytest.fixture
def runner(task_mgr):
    adapter = FakeAdapter()
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    return TaskRunner(
        task_manager=task_mgr,
        adapter=adapter,
        model="fake-model",
        router=router,
        ctx=ctx,
    )


@pytest.mark.asyncio
async def test_run_completes_and_notifies(runner, task_mgr):
    task = task_mgr.create(subject="后台任务")

    await runner.run(task.id, prompt="做点什么")
    await asyncio.sleep(0.3)

    notifications = await runner.drain_notifications()
    assert len(notifications) == 1
    assert notifications[0].task_id == task.id
    assert notifications[0].status == RuntimeTaskStatus.COMPLETED

    updated = task_mgr.get(task.id)
    assert updated.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_drain_empty_when_no_notifications(runner, task_mgr):
    results = await runner.drain_notifications()
    assert results == []


@pytest.mark.asyncio
async def test_runner_updates_task_to_in_progress(runner, task_mgr):
    task = task_mgr.create(subject="立即检查")
    await runner.run(task.id, prompt="开始")

    found = task_mgr.get(task.id)
    assert found.status == TaskStatus.IN_PROGRESS

    await asyncio.sleep(0.3)
    await runner.drain_notifications()
