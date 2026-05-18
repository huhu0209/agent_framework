"""update_plan_status 工具测试。"""

import pytest

from agent_framework.orchestrator.planner import PlanItem, PlanningState
from agent_framework.tools.builtin.plan_tools import handle_update_plan_status
from agent_framework.tools.types import ToolUseContext


def _make_ctx(state: PlanningState | None = None) -> ToolUseContext:
    extra = {}
    if state is not None:
        extra["planning_state"] = state
    return ToolUseContext(extra=extra)


def _make_state() -> PlanningState:
    return PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="pending"),
            PlanItem(id="2", action="步骤二", status="pending"),
        ],
        current_focus=None,
        plan_source="caller_injected",
    )


@pytest.mark.asyncio
async def test_update_plan_status_normal():
    state = _make_state()
    ctx = _make_ctx(state)
    result = await handle_update_plan_status({"item_id": "1", "status": "in_progress"}, ctx)
    assert not result.is_error
    assert "in_progress" in result.content
    assert state.items[0].status == "in_progress"


@pytest.mark.asyncio
async def test_update_plan_status_no_planning_state():
    ctx = _make_ctx()
    result = await handle_update_plan_status({"item_id": "1", "status": "in_progress"}, ctx)
    assert result.is_error
    assert "没有活跃计划" in result.content


@pytest.mark.asyncio
async def test_update_plan_status_invalid_transition():
    state = _make_state()
    ctx = _make_ctx(state)
    result = await handle_update_plan_status({"item_id": "1", "status": "completed"}, ctx)
    assert result.is_error
    assert "Invalid transition" in result.content


@pytest.mark.asyncio
async def test_update_plan_status_unknown_item():
    state = _make_state()
    ctx = _make_ctx(state)
    result = await handle_update_plan_status({"item_id": "99", "status": "in_progress"}, ctx)
    assert result.is_error
    assert "Unknown" in result.content
