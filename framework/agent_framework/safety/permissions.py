"""权限管道 — DENY → MODE → ALLOW → ASK 四步级联。"""

from __future__ import annotations

from enum import Enum
from typing import Any

from agent_framework.config.loader import ConfigLoader
from agent_framework.config.settings import Settings
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


class PermissionPipeline:
    """四步级联权限检查。"""

    def __init__(
        self,
        profile: AgentProfile,
        critical_tools: frozenset[str] = frozenset(),
    ) -> None:
        self._profile = profile
        self._critical_tools = critical_tools
        self._annotations: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_loader(
        cls,
        loader: ConfigLoader,
        profile_name: str,
        *,
        _profile: AgentProfile | None = None,
    ) -> PermissionPipeline:
        """从 ConfigLoader 加载 profile 和 settings，合并权限配置。

        调用 AgentProfile.from_profile(loader, profile_name) 获取 profile，
        再从 loader.load_settings() 获取 Settings，将 settings.permissions
        的 allow/deny 合并到 profile 的 allowed_tools/disallowed_tools。
        不重复添加已存在的工具名。

        _profile 参数仅用于测试注入，生产代码不传此参数。
        """
        profile = _profile if _profile is not None else AgentProfile.from_profile(loader, profile_name)
        settings = loader.load_settings()

        allowed = list(profile.allowed_tools or [])
        for tool in settings.permissions.allow:
            if tool not in allowed:
                allowed.append(tool)

        disallowed = list(profile.disallowed_tools or [])
        for tool in settings.permissions.deny:
            if tool not in disallowed:
                disallowed.append(tool)

        merged_profile = profile.model_copy(update={
            "allowed_tools": allowed,
            "disallowed_tools": disallowed,
        })
        return cls(profile=merged_profile)

    def register_annotations(self, tool_name: str, annotations: dict[str, Any]) -> None:
        """注册工具的注解信息。"""
        self._annotations[tool_name] = annotations

    def check(self, tool_name: str, tool_input: dict) -> PermissionResult:
        """执行四步级联权限检查。"""

        # ① DENY — 黑名单 + 高危工具
        if tool_name in self._critical_tools:
            return PermissionResult(PermissionDecision.DENY, "critical", RiskLevel.CRITICAL)

        disallowed = self._profile.disallowed_tools
        if disallowed is not None and tool_name in disallowed:
            return PermissionResult(PermissionDecision.DENY, "disallowed", RiskLevel.HIGH)

        # ② MODE
        mode = self._profile.permission_mode
        if mode == "deny":
            return PermissionResult(PermissionDecision.DENY, "mode_deny", RiskLevel.HIGH)
        if mode == "accept":
            # B3: accept 模式不一键放行——destructive/openWorld 工具仍需询问，
            # 其余工具放行。避免 accept 模式下 write_file 等危险操作绕过 HITL。
            annotations = self._annotations.get(tool_name, {})
            if annotations.get("destructive") or annotations.get("openWorld"):
                return self._annotate_decision(tool_name)
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
