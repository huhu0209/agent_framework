"""Session Planning — 数据模型、状态管理、内联解析。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class DriftLevel(Enum):
    NONE = "none"
    WARN = "warn"
    ABORT = "abort"


@dataclass
class PlanItem:
    id: str
    action: str
    status: Literal["pending", "in_progress", "completed", "blocked"]


@dataclass
class PlanSnapshot:
    items: list[PlanItem]
    completed_count: int
    total_count: int
    current_focus: str | None
    plan_source: Literal["llm_generated", "caller_injected", "none"]


_VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress"],
    "in_progress": ["completed", "blocked"],
    "completed": [],
    "blocked": ["in_progress"],
}


@dataclass
class PlanningState:
    items: list[PlanItem]
    current_focus: str | None
    drift_count: int = 0
    plan_source: Literal["llm_generated", "caller_injected"] = "llm_generated"

    def update_status(self, item_id: str, new_status: str) -> None:
        item = next((i for i in self.items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"Unknown plan item: {item_id}")

        allowed = _VALID_TRANSITIONS.get(item.status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid transition: {item.status} -> {new_status}")

        item.status = new_status
        if new_status != "blocked":
            self.drift_count = 0
        if new_status == "in_progress":
            self.current_focus = item_id

    def check_drift(self, warn_threshold: int, abort_threshold: int) -> DriftLevel:
        if self.drift_count >= abort_threshold:
            return DriftLevel.ABORT
        if self.drift_count >= warn_threshold:
            return DriftLevel.WARN
        return DriftLevel.NONE

    def format_for_injection(self) -> str:
        lines = ["当前计划进度："]
        for item in self.items:
            lines.append(f"  {item.id}. [{item.status}] {item.action}")
        return "\n".join(lines)

    def snapshot(self) -> PlanSnapshot:
        return PlanSnapshot(
            items=[PlanItem(id=i.id, action=i.action, status=i.status) for i in self.items],
            completed_count=sum(1 for i in self.items if i.status == "completed"),
            total_count=len(self.items),
            current_focus=self.current_focus,
            plan_source=self.plan_source,
        )
