"""Session-scoped plan lifecycle manager."""

from __future__ import annotations

from agent_framework.orchestrator.planner import (
    DriftLevel,
    PlanItem,
    PlanSnapshot,
    PlanningState,
    PLAN_PROGRESS_PREFIX,
    parse_plan_response,
)
from agent_framework.prompts.templates import (
    DRIFT_WARN_PREFIX,
    DRIFT_WARN_TEMPLATE,
    PLAN_GENERATION_INSTRUCTION,
)


class PlanningSession:
    """Manage plan creation, status transitions, and drift detection."""

    def __init__(
        self,
        allow_replan: bool = False,
        drift_warn: int = 3,
        drift_abort: int = 8,
    ) -> None:
        self._allow_replan = allow_replan
        self._drift_warn = drift_warn
        self._drift_abort = drift_abort
        self._state: PlanningState | None = None

    @property
    def has_plan(self) -> bool:
        return self._state is not None

    @property
    def drift_count(self) -> int:
        if self._state is None:
            return 0
        return self._state.drift_count

    def create_from_items(self, items: list[PlanItem], source: str) -> None:
        self._state = PlanningState(
            items=[PlanItem(id=i.id, action=i.action, status=i.status) for i in items],
            current_focus=None,
            plan_source=source,
        )

    def try_parse_from_response(self, text: str) -> bool:
        if self._state is not None and not self._allow_replan:
            return False
        parsed = parse_plan_response(text)
        if parsed is None:
            return False
        self._state = PlanningState(
            items=parsed,
            current_focus=None,
            plan_source="llm_generated",
        )
        return True

    def update_status(self, item_id: str, new_status: str) -> None:
        if self._state is None:
            raise ValueError("No plan loaded")
        self._state = self._state.update_status(item_id, new_status)

    def snapshot(self) -> PlanSnapshot | None:
        if self._state is None:
            return None
        return self._state.snapshot()

    def increment_drift(self) -> DriftLevel:
        if self._state is None:
            return DriftLevel.NONE
        self._state = self._state.increment_drift()
        return self._state.check_drift(self._drift_warn, self._drift_abort)

    def reset_drift(self) -> None:
        if self._state is not None:
            self._state = self._state.with_drift_reset()

    def format_context_message(self) -> tuple[str, str]:
        if self._state is None:
            return ("", "")
        plan_text = self._state.format_for_injection()
        drift_level = self._state.check_drift(self._drift_warn, self._drift_abort)
        if drift_level == DriftLevel.WARN:
            drift_text = DRIFT_WARN_TEMPLATE.format(
                drift_count=self._state.drift_count,
                plan_text=plan_text,
            )
        else:
            drift_text = ""
        return (drift_text, plan_text)

    def is_plan_context_text(self, text: str) -> bool:
        return text.startswith(PLAN_PROGRESS_PREFIX) or text.startswith(DRIFT_WARN_PREFIX)

    @staticmethod
    def plan_instruction_prompt() -> str:
        return PLAN_GENERATION_INSTRUCTION
