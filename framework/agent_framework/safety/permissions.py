"""权限管道 — DENY → MODE → ALLOW → ASK 四步级联。"""

from __future__ import annotations

from enum import Enum
from typing import Any

from agent_framework.prompts.profiles import AgentProfile


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionResult:
    """权限检查结果。"""

    def __init__(
        self,
        action: PermissionDecision,
        reason: str,
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> None:
        self.action = action
        self.reason = reason
        self.risk_level = risk_level


# 全局高危工具列表
_CRITICAL_TOOLS: set[str] = set()


class PermissionPipeline:
    """四步级联权限检查。"""

    def __init__(self, profile: AgentProfile) -> None:
        self._profile = profile
        self._annotations: dict[str, dict[str, Any]] = {}

    def register_annotations(self, tool_name: str, annotations: dict[str, Any]) -> None:
        """注册工具的注解信息。"""
        self._annotations[tool_name] = annotations

    def check(self, tool_name: str, tool_input: dict) -> PermissionResult:
        """执行四步级联权限检查。"""

        # ① DENY — 黑名单 + 全局高危
        if tool_name in _CRITICAL_TOOLS:
            return PermissionResult(PermissionDecision.DENY, "critical", RiskLevel.CRITICAL)

        disallowed = self._profile.disallowed_tools
        if disallowed is not None and tool_name in disallowed:
            return PermissionResult(PermissionDecision.DENY, "disallowed", RiskLevel.HIGH)

        # ② MODE
        mode = self._profile.permission_mode
        if mode == "deny":
            return PermissionResult(PermissionDecision.DENY, "mode_deny", RiskLevel.HIGH)
        if mode == "accept":
            return PermissionResult(PermissionDecision.ALLOW, "mode_accept", RiskLevel.SAFE)

        # ③ ALLOW — 白名单
        allowed = self._profile.allowed_tools
        if allowed is not None and tool_name in allowed:
            return PermissionResult(PermissionDecision.ALLOW, "allowed", RiskLevel.SAFE)

        # ④ ASK — 注解驱动自动决策
        return self._annotate_decision(tool_name)

    def _annotate_decision(self, tool_name: str) -> PermissionResult:
        """根据工具注解决定是否需要询问。"""
        annotations = self._annotations.get(tool_name, {})

        is_readonly = annotations.get("readOnly", False)
        is_destructive = annotations.get("destructive", False)
        is_idempotent = annotations.get("idempotent", False)
        is_open_world = annotations.get("openWorld", False)

        # readOnly → 自动通过
        if is_readonly:
            return PermissionResult(PermissionDecision.ALLOW, "readOnly", RiskLevel.SAFE)

        # idempotent + !destructive → 自动通过
        if is_idempotent and not is_destructive:
            return PermissionResult(PermissionDecision.ALLOW, "idempotent_safe", RiskLevel.LOW)

        # destructive + !idempotent → HIGH
        if is_destructive and not is_idempotent:
            return PermissionResult(PermissionDecision.ASK, "destructive", RiskLevel.HIGH)

        # openWorld → MEDIUM
        if is_open_world:
            return PermissionResult(PermissionDecision.ASK, "openWorld", RiskLevel.MEDIUM)

        # destructive + idempotent → MEDIUM
        if is_destructive:
            return PermissionResult(PermissionDecision.ASK, "destructive_idempotent", RiskLevel.MEDIUM)

        # 无注解 → LOW ASK
        return PermissionResult(PermissionDecision.ASK, "unknown", RiskLevel.LOW)
