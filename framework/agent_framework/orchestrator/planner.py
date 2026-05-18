"""Session Planning — 数据模型、状态管理、内联解析。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class DriftLevel(Enum):
    NONE = "none"  # 无偏离
    WARN = "warn"  # 警告
    ABORT = "abort"  # 中止


@dataclass
class PlanItem:
    id: str
    action: str
    status: Literal["pending", "in_progress", "completed", "blocked"]  # 计划中的单个步骤状态


@dataclass
class PlanSnapshot:
    """计划快照。"""
    items: list[PlanItem]  # 计划中的所有步骤
    completed_count: int  # 已完成的步骤数
    total_count: int  # 总步骤数
    current_focus: str | None  # 当前关注的步骤 ID
    plan_source: Literal["llm_generated", "caller_injected", "none"]  # 计划来源类型：LLM 生成、调用注入、无


_VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress"],
    "in_progress": ["completed", "blocked"],
    "completed": [],
    "blocked": ["in_progress"],
}


@dataclass
class PlanningState:
    """计划状态。"""
    items: list[PlanItem]  # 计划中的所有步骤
    current_focus: str | None  # 当前关注的步骤 ID
    drift_count: int = 0  # 计划偏离次数
    plan_source: Literal["llm_generated", "caller_injected"] = "llm_generated"  # 计划来源类型：LLM 生成、调用注入

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
        """
        检查计划偏离程度。
        :param warn_threshold: 警告阈值，超过后返回 DriftLevel.WARN。
        :param abort_threshold: 中止阈值，超过后返回 DriftLevel.ABORT。
        :return: 计划偏离程度。
        """
        has_active = any(i.status == "in_progress" for i in self.items)
        has_pending = any(i.status == "pending" for i in self.items)
        # 如果有活跃步骤或没有待处理步骤，返回无偏离
        if has_active or not has_pending:
            return DriftLevel.NONE

        # 如果偏离次数超过中止阈值，返回中止
        if self.drift_count >= abort_threshold:
            return DriftLevel.ABORT
        # 如果偏离次数超过警告阈值，返回警告
        if self.drift_count >= warn_threshold:
            return DriftLevel.WARN
        # 否则返回无偏离
        return DriftLevel.NONE

    def format_for_injection(self) -> str:
        """
        格式化计划进度，用于注入到 LLM 提示中。
        """
        lines = ["当前计划进度："]
        for item in self.items:
            lines.append(f"  {item.id}. [{item.status}] {item.action}")
        return "\n".join(lines)

    def snapshot(self) -> PlanSnapshot:
        """
        生成计划快照。
        """
        return PlanSnapshot(
            items=[PlanItem(id=i.id, action=i.action, status=i.status) for i in self.items],
            completed_count=sum(1 for i in self.items if i.status == "completed"),
            total_count=len(self.items),
            current_focus=self.current_focus,
            plan_source=self.plan_source,
        )
