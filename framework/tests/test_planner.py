"""Planning 数据模型和解析逻辑测试。"""

import pytest

from agent_framework.orchestrator.planner import (
    DriftLevel,
    PlanItem,
    PlanSnapshot,
    PlanningState,
)


# --- PlanItem ---


def test_plan_item_creation():
    item = PlanItem(id="1", action="搜索模块", status="pending")
    assert item.id == "1"
    assert item.action == "搜索模块"
    assert item.status == "pending"


# --- PlanningState.update_status 正常转换 ---


def test_update_status_pending_to_in_progress():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="pending"),
        ],
        current_focus=None,
    )
    state.update_status("1", "in_progress")
    assert state.items[0].status == "in_progress"
    assert state.current_focus == "1"
    assert state.drift_count == 0


def test_update_status_in_progress_to_completed():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="in_progress"),
        ],
        current_focus="1",
        drift_count=2,
    )
    state.update_status("1", "completed")
    assert state.items[0].status == "completed"
    assert state.drift_count == 0


def test_update_status_in_progress_to_blocked():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="in_progress"),
        ],
        current_focus="1",
        drift_count=2,
    )
    state.update_status("1", "blocked")
    assert state.items[0].status == "blocked"
    assert state.drift_count == 2  # blocked 不重置 drift


def test_update_status_blocked_to_in_progress():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="blocked"),
        ],
        current_focus=None,
    )
    state.update_status("1", "in_progress")
    assert state.items[0].status == "in_progress"
    assert state.current_focus == "1"


# --- PlanningState.update_status 非法转换 ---


def test_update_status_invalid_transition():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="pending"),
        ],
        current_focus=None,
    )
    with pytest.raises(ValueError, match="Invalid transition"):
        state.update_status("1", "completed")


def test_update_status_completed_is_terminal():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="completed"),
        ],
        current_focus=None,
    )
    with pytest.raises(ValueError, match="Invalid transition"):
        state.update_status("1", "in_progress")


def test_update_status_unknown_item():
    state = PlanningState(items=[], current_focus=None)
    with pytest.raises(ValueError, match="Unknown plan item"):
        state.update_status("99", "in_progress")


# --- check_drift ---


def test_check_drift_none():
    state = PlanningState(
        items=[PlanItem(id="1", action="步骤", status="in_progress")],
        current_focus="1",
        drift_count=1,
    )
    assert state.check_drift(warn_threshold=3, abort_threshold=8) == DriftLevel.NONE


def test_check_drift_warn():
    state = PlanningState(
        items=[PlanItem(id="1", action="步骤", status="in_progress")],
        current_focus="1",
        drift_count=3,
    )
    assert state.check_drift(warn_threshold=3, abort_threshold=8) == DriftLevel.WARN


def test_check_drift_abort():
    state = PlanningState(
        items=[PlanItem(id="1", action="步骤", status="in_progress")],
        current_focus="1",
        drift_count=8,
    )
    assert state.check_drift(warn_threshold=3, abort_threshold=8) == DriftLevel.ABORT


def test_check_drift_skips_blocked_items():
    """blocked item 不计入 drift 检测。"""
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="blocked"),
            PlanItem(id="2", action="步骤二", status="pending"),
        ],
        current_focus=None,
        drift_count=5,
    )
    # 所有非 blocked 的 item 都是 pending（无 in_progress），算偏离
    assert state.check_drift(warn_threshold=3, abort_threshold=8) == DriftLevel.WARN


# --- snapshot ---


def test_snapshot():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="步骤一", status="completed"),
            PlanItem(id="2", action="步骤二", status="in_progress"),
        ],
        current_focus="2",
        plan_source="caller_injected",
    )
    snap = state.snapshot()
    assert isinstance(snap, PlanSnapshot)
    assert snap.completed_count == 1
    assert snap.total_count == 2
    assert snap.current_focus == "2"
    assert snap.plan_source == "caller_injected"


# --- format_for_injection ---


def test_format_for_injection():
    state = PlanningState(
        items=[
            PlanItem(id="1", action="搜索模块", status="completed"),
            PlanItem(id="2", action="重构代码", status="in_progress"),
            PlanItem(id="3", action="更新测试", status="pending"),
        ],
        current_focus="2",
        plan_source="llm_generated",
    )
    text = state.format_for_injection()
    assert "[completed]" in text
    assert "[in_progress]" in text
    assert "[pending]" in text
    assert "搜索模块" in text
    assert "重构代码" in text
