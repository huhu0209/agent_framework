"""Session Planning — 数据模型、状态管理、内联解析。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Literal


PLAN_PROGRESS_PREFIX = "当前计划进度："

PlanSource = Literal["llm_generated", "caller_injected", "none"]


class DriftLevel(Enum):
    NONE = "none"  # 无偏离
    WARN = "warn"  # 警告
    ABORT = "abort"  # 中止


@dataclass(frozen=True)
class PlanItem:
    id: str
    action: str
    status: Literal["pending", "in_progress", "completed", "blocked"]  # 计划中的单个步骤状态


@dataclass(frozen=True)
class PlanSnapshot:
    """计划快照。"""
    items: tuple[PlanItem, ...]  # 计划中的所有步骤
    completed_count: int  # 已完成的步骤数
    total_count: int  # 总步骤数
    current_focus: str | None  # 当前关注的步骤 ID
    plan_source: PlanSource  # 计划来源类型：LLM 生成、调用注入、无


_VALID_TRANSITIONS = MappingProxyType({
    "pending": ("in_progress",),
    "in_progress": ("completed", "blocked"),
    "completed": (),
    "blocked": ("in_progress",),
})

VALID_PLAN_STATUSES = frozenset(_VALID_TRANSITIONS.keys())


@dataclass(frozen=True)
class PlanningState:
    """计划状态（不可变）。所有状态变更返回新实例。"""
    items: tuple[PlanItem, ...]  # 计划中的所有步骤
    current_focus: str | None  # 当前关注的步骤 ID
    drift_count: int = 0  # 计划偏离次数
    plan_source: Literal["llm_generated", "caller_injected"] = "llm_generated"  # 计划来源类型：LLM 生成、调用注入

    def update_status(self, item_id: str, new_status: str) -> PlanningState:
        """返回状态更新后的新 PlanningState 实例。"""
        item = next((i for i in self.items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"Unknown plan item: {item_id}")

        allowed = _VALID_TRANSITIONS.get(item.status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid transition: {item.status} -> {new_status}")

        new_items = tuple(
            PlanItem(id=i.id, action=i.action, status=new_status) if i.id == item_id else i
            for i in self.items
        )
        # blocked 保留 drift_count：阻塞解除后继续追踪偏离；
        # 其他状态转换（completed 等）重置，因为步骤已推进。
        new_drift = self.drift_count if new_status == "blocked" else 0
        new_focus = item_id if new_status == "in_progress" else self.current_focus
        return PlanningState(
            items=new_items,
            current_focus=new_focus,
            drift_count=new_drift,
            plan_source=self.plan_source,
        )

    def increment_drift(self) -> PlanningState:
        """返回 drift_count +1 的新 PlanningState 实例。"""
        return PlanningState(
            items=self.items,
            current_focus=self.current_focus,
            drift_count=self.drift_count + 1,
            plan_source=self.plan_source,
        )

    def with_drift_reset(self) -> PlanningState:
        """返回 drift_count 重置为 0 的新 PlanningState 实例。"""
        return PlanningState(
            items=self.items,
            current_focus=self.current_focus,
            drift_count=0,
            plan_source=self.plan_source,
        )

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
        lines = [PLAN_PROGRESS_PREFIX]
        for item in self.items:
            lines.append(f"  {item.id}. [{item.status}] {item.action}")
        return "\n".join(lines)

    def snapshot(self) -> PlanSnapshot:
        """
        生成计划快照。
        """
        return PlanSnapshot(
            items=self.items,
            completed_count=sum(1 for i in self.items if i.status == "completed"),
            total_count=len(self.items),
            current_focus=self.current_focus,
            plan_source=self.plan_source,
        )


def parse_plan_response(text: str) -> list[PlanItem] | None:
    """从 LLM 回复文本中提取 <plan> 块。"""
    match = re.search(r"<plan>(.*?)</plan>", text, re.DOTALL)
    if not match:
        return None

    items: list[PlanItem] = []
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\.\s*(.*)", line)
        if m:
            items.append(PlanItem(id=m.group(1), action=m.group(2), status="pending"))
        elif items:
            items[-1] = PlanItem(
                id=items[-1].id,
                action=items[-1].action + " " + line,
                status=items[-1].status,
            )

    return items if items else None


def strip_plan_tags(text: str) -> str:
    """移除文本中的 <plan>...</plan> 块。"""
    return re.sub(r"<plan>.*?</plan>", "", text, flags=re.DOTALL).strip()
