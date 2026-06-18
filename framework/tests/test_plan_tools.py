"""update_plan_status 工具测试。"""

import pytest

from agent_framework.orchestrator.planner import PlanItem
from agent_framework.orchestrator.planning_session import PlanningSession
from agent_framework.tools.builtin.plan_tools import handle_update_plan_status
from agent_framework.tools.types import ToolUseContext


def _make_ctx(session: PlanningSession | None = None) -> ToolUseContext:
    extra = {}
    if session is not None:
        extra["planning_session"] = session
    return ToolUseContext(extra=extra)


def _make_session() -> PlanningSession:
    session = PlanningSession()
    session.create_from_items([
        PlanItem(id="1", action="步骤一", status="pending"),
        PlanItem(id="2", action="步骤二", status="pending"),
    ], "caller_injected")
    return session


@pytest.mark.asyncio
async def test_update_plan_status_normal():
    session = _make_session()
    ctx = _make_ctx(session)
    result = await handle_update_plan_status({"item_id": "1", "status": "in_progress"}, ctx)
    assert not result.is_error
    assert "in_progress" in result.content
    assert session.snapshot().current_focus == "1"


@pytest.mark.asyncio
async def test_update_plan_status_no_planning_session():
    ctx = _make_ctx()
    result = await handle_update_plan_status({"item_id": "1", "status": "in_progress"}, ctx)
    assert result.is_error
    assert "没有活跃计划" in result.content


@pytest.mark.asyncio
async def test_update_plan_status_invalid_transition():
    session = _make_session()
    ctx = _make_ctx(session)
    result = await handle_update_plan_status({"item_id": "1", "status": "completed"}, ctx)
    assert result.is_error
    assert "Invalid transition" in result.content


@pytest.mark.asyncio
async def test_update_plan_status_unknown_item():
    session = _make_session()
    ctx = _make_ctx(session)
    result = await handle_update_plan_status({"item_id": "99", "status": "in_progress"}, ctx)
    assert result.is_error
    assert "Unknown" in result.content
