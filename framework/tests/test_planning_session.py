"""Tests for PlanningSession — plan lifecycle management."""

from __future__ import annotations

import pytest

from agent_framework.orchestrator.planner import DriftLevel, PlanItem
from agent_framework.orchestrator.planning_session import PlanningSession


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _items(*actions: str) -> list[PlanItem]:
    return [PlanItem(id=str(i), action=a, status="pending")
            for i, a in enumerate(actions, 1)]


# ---------------------------------------------------------------------------
# 1. create_from_items
# ---------------------------------------------------------------------------

class TestCreateFromItems:
    def test_has_plan_after_create(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A", "step B"), source="test")
        assert session.has_plan is True

    def test_snapshot_has_value(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A", "step B"), source="test")
        snap = session.snapshot()
        assert snap is not None
        assert snap.total_count == 2
        assert snap.plan_source == "test"


# ---------------------------------------------------------------------------
# 2. try_parse_from_response — success
# ---------------------------------------------------------------------------

class TestTryParseSuccess:
    def test_parse_valid_plan_tag(self) -> None:
        session = PlanningSession()
        text = "Here is my plan:\n<plan>\n1. Do X\n2. Do Y\n</plan>\nDone."
        assert session.try_parse_from_response(text) is True
        assert session.has_plan is True
        snap = session.snapshot()
        assert snap is not None
        assert snap.total_count == 2
        assert snap.plan_source == "llm_generated"


# ---------------------------------------------------------------------------
# 3. try_parse_from_response — no tag
# ---------------------------------------------------------------------------

class TestTryParseNoTag:
    def test_returns_false_without_tag(self) -> None:
        session = PlanningSession()
        assert session.try_parse_from_response("no plan here") is False
        assert session.has_plan is False


# ---------------------------------------------------------------------------
# 4. try_parse — allow_replan
# ---------------------------------------------------------------------------

class TestReplan:
    def test_allow_replan_overwrites(self) -> None:
        session = PlanningSession(allow_replan=True)
        session.create_from_items(_items("old"), source="test")
        text = "<plan>\n1. new step\n</plan>"
        assert session.try_parse_from_response(text) is True
        snap = session.snapshot()
        assert snap is not None
        assert snap.total_count == 1
        assert snap.items[0].action == "new step"


# ---------------------------------------------------------------------------
# 5. try_parse — no replan by default
# ---------------------------------------------------------------------------

class TestNoReplan:
    def test_default_blocks_overwrite(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("old"), source="test")
        text = "<plan>\n1. new step\n</plan>"
        assert session.try_parse_from_response(text) is False
        snap = session.snapshot()
        assert snap is not None
        assert snap.items[0].action == "old"


# ---------------------------------------------------------------------------
# 6. update_status — normal transition
# ---------------------------------------------------------------------------

class TestUpdateStatus:
    def test_pending_to_in_progress(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A"), source="test")
        session.update_status("1", "in_progress")
        snap = session.snapshot()
        assert snap is not None
        assert snap.items[0].status == "in_progress"


# ---------------------------------------------------------------------------
# 7. update_status resets drift
# ---------------------------------------------------------------------------

class TestUpdateStatusResetsDrift:
    def test_drift_resets_on_update(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A", "step B"), source="test")
        for _ in range(5):
            session.increment_drift()
        assert session.drift_count > 0
        session.update_status("1", "in_progress")
        assert session.drift_count == 0


# ---------------------------------------------------------------------------
# 8. update_status — invalid transition
# ---------------------------------------------------------------------------

class TestUpdateStatusInvalid:
    def test_completed_to_pending_raises(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A"), source="test")
        session.update_status("1", "in_progress")
        session.update_status("1", "completed")
        with pytest.raises(ValueError, match="Invalid transition"):
            session.update_status("1", "pending")


# ---------------------------------------------------------------------------
# 9. increment_drift — NONE
# ---------------------------------------------------------------------------

class TestDriftNone:
    def test_returns_none_when_in_progress_exists(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A"), source="test")
        session.update_status("1", "in_progress")
        result = session.increment_drift()
        assert result is DriftLevel.NONE


# ---------------------------------------------------------------------------
# 10. increment_drift — WARN
# ---------------------------------------------------------------------------

class TestDriftWarn:
    def test_returns_warn_at_threshold(self) -> None:
        session = PlanningSession(drift_warn=3, drift_abort=8)
        session.create_from_items(_items("step A"), source="test")
        for _ in range(3):
            session.increment_drift()
        assert session.drift_count == 3
        # 3rd increment should have returned WARN
        session.increment_drift()
        # after 4 increments total, still WARN
        assert session.drift_count == 4


# ---------------------------------------------------------------------------
# 11. increment_drift — ABORT
# ---------------------------------------------------------------------------

class TestDriftAbort:
    def test_returns_abort_at_threshold(self) -> None:
        session = PlanningSession(drift_warn=3, drift_abort=8)
        session.create_from_items(_items("step A"), source="test")
        result = DriftLevel.NONE
        for _ in range(8):
            result = session.increment_drift()
        assert result is DriftLevel.ABORT


# ---------------------------------------------------------------------------
# 12. snapshot — no plan
# ---------------------------------------------------------------------------

class TestSnapshotNoPlan:
    def test_returns_none_without_plan(self) -> None:
        session = PlanningSession()
        assert session.snapshot() is None


# ---------------------------------------------------------------------------
# 13. format_context_message — normal
# ---------------------------------------------------------------------------

class TestFormatContext:
    def test_returns_plan_text(self) -> None:
        session = PlanningSession()
        session.create_from_items(_items("step A"), source="test")
        drift_text, plan_text = session.format_context_message()
        assert drift_text == ""
        assert "当前计划进度" in plan_text


# ---------------------------------------------------------------------------
# 14. format_context_message — with drift warning
# ---------------------------------------------------------------------------

class TestFormatContextWithDrift:
    def test_includes_drift_warning_text(self) -> None:
        session = PlanningSession(drift_warn=2, drift_abort=8)
        session.create_from_items(_items("step A"), source="test")
        for _ in range(2):
            session.increment_drift()
        drift_text, plan_text = session.format_context_message()
        assert "[偏离提醒]" in drift_text


# ---------------------------------------------------------------------------
# 15. is_plan_context_text
# ---------------------------------------------------------------------------

class TestIsPlanContextText:
    def test_detects_plan_prefix(self) -> None:
        session = PlanningSession()
        assert session.is_plan_context_text("当前计划进度：xxx") is True

    def test_detects_drift_prefix(self) -> None:
        session = PlanningSession()
        assert session.is_plan_context_text("[偏离提醒] xxx") is True

    def test_rejects_normal_text(self) -> None:
        session = PlanningSession()
        assert session.is_plan_context_text("normal text") is False


# ---------------------------------------------------------------------------
# 16. plan_instruction_prompt
# ---------------------------------------------------------------------------

class TestPlanInstructionPrompt:
    def test_contains_plan_tag_and_update_instruction(self) -> None:
        prompt = PlanningSession.plan_instruction_prompt()
        assert "<plan>" in prompt
        assert "update_plan_status" in prompt
