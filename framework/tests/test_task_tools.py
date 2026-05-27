"""Task 工具测试 — create/update/list/get。"""

import pytest

from agent_framework.tasks.manager import TaskManager
from agent_framework.tasks.tools import create_task_tools
from agent_framework.tools.types import ToolUseContext


@pytest.fixture
def task_mgr(tmp_path):
    return TaskManager(tmp_path / "tasks")


@pytest.fixture
def tools(task_mgr):
    return {t.name: t for t in create_task_tools(task_mgr)}


ctx = ToolUseContext()


@pytest.mark.asyncio
async def test_task_create(tools, task_mgr):
    handler = tools["task_create"].handler
    result = await handler({"subject": "新任务", "description": "详情"}, ctx)
    assert result.is_error is False
    assert "已创建" in result.content
    assert "新任务" in result.content


@pytest.mark.asyncio
async def test_task_update_status(tools, task_mgr):
    task_mgr.create(subject="工作")
    handler = tools["task_update"].handler
    result = await handler({"id": "1", "status": "in_progress"}, ctx)
    assert result.is_error is False
    assert "in_progress" in result.content


@pytest.mark.asyncio
async def test_task_update_invalid_status(tools, task_mgr):
    task_mgr.create(subject="已完成")
    task_mgr.update("1", status="in_progress")
    task_mgr.update("1", status="completed")
    handler = tools["task_update"].handler
    result = await handler({"id": "1", "status": "in_progress"}, ctx)
    assert result.is_error is True


@pytest.mark.asyncio
async def test_task_list(tools, task_mgr):
    task_mgr.create(subject="任务A")
    task_mgr.create(subject="任务B")
    handler = tools["task_list"].handler
    result = await handler({}, ctx)
    assert result.is_error is False
    assert "任务A" in result.content
    assert "任务B" in result.content


@pytest.mark.asyncio
async def test_task_get(tools, task_mgr):
    task_mgr.create(subject="查找我", description="详细描述")
    handler = tools["task_get"].handler
    result = await handler({"id": "1"}, ctx)
    assert result.is_error is False
    assert "查找我" in result.content
    assert "详细描述" in result.content


@pytest.mark.asyncio
async def test_task_get_missing(tools):
    handler = tools["task_get"].handler
    result = await handler({"id": "999"}, ctx)
    assert result.is_error is True
    assert "不存在" in result.content


@pytest.mark.asyncio
async def test_task_create_over_limit(tools, task_mgr):
    from agent_framework.tasks.manager import MAX_ACTIVE_TASKS
    for i in range(MAX_ACTIVE_TASKS):
        task_mgr.create(subject=f"t-{i}")
    handler = tools["task_create"].handler
    result = await handler({"subject": "overflow"}, ctx)
    assert result.is_error is True


@pytest.mark.asyncio
async def test_four_tools_returned(tools):
    assert set(tools.keys()) == {"task_create", "task_update", "task_list", "task_get"}
