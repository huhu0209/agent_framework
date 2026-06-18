"""权限管道测试。"""

import pytest
from unittest.mock import MagicMock

from agent_framework.config.loader import ConfigLoader
from agent_framework.config.settings import PermissionsConfig, Settings
from agent_framework.prompts.profiles import AgentProfile
from agent_framework.safety.permissions import (
    PermissionDecision,
    PermissionPipeline,
    PermissionResult,
    RiskLevel,
)


class TestPermissionPipeline:
    def test_deny_disallowed_tool(self):
        profile = AgentProfile(
            name="reader",
            description="只读",
            soul="", agents_rules="", identity="",
            disallowed_tools=["write_file"],
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.DENY
        assert decision.reason == "disallowed"

    def test_allow_whitelisted_tool(self):
        profile = AgentProfile(
            name="reader",
            description="只读",
            soul="", agents_rules="", identity="",
            allowed_tools=["read_file"],
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("read_file", {})
        assert decision.action == PermissionDecision.ALLOW
        assert decision.reason == "allowed"

    def test_accept_mode_allows_all(self):
        profile = AgentProfile(
            name="admin",
            description="admin",
            soul="", agents_rules="", identity="",
            permission_mode="accept",
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.ALLOW

    def test_deny_mode_blocks_all(self):
        profile = AgentProfile(
            name="locked",
            description="locked",
            soul="", agents_rules="", identity="",
            permission_mode="deny",
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("read_file", {})
        assert decision.action == PermissionDecision.DENY

    def test_readonly_annotation_auto_approves(self):
        profile = AgentProfile(
            name="default",
            description="default",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("read_file", {"readOnly": True})

        decision = pipeline.check("read_file", {})
        assert decision.action == PermissionDecision.ALLOW
        assert decision.reason == "readOnly"

    def test_destructive_annotation_requires_ask(self):
        profile = AgentProfile(
            name="default",
            description="default",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("write_file", {"destructive": True})

        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.ASK
        assert decision.risk_level == RiskLevel.HIGH

    def test_unknown_tool_in_ask_mode(self):
        profile = AgentProfile(
            name="default",
            description="default",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("unknown_tool", {})
        assert decision.action == PermissionDecision.ASK
        assert decision.risk_level == RiskLevel.LOW

    def test_idempotent_safe_auto_approves(self):
        profile = AgentProfile(
            name="default",
            description="default",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("status_check", {"idempotent": True})

        decision = pipeline.check("status_check", {})
        assert decision.action == PermissionDecision.ALLOW

    def test_openworld_requires_ask_medium(self):
        profile = AgentProfile(
            name="default",
            description="default",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("web_request", {"openWorld": True})

        decision = pipeline.check("web_request", {})
        assert decision.action == PermissionDecision.ASK
        assert decision.risk_level == RiskLevel.MEDIUM

    def test_whitelist_overrides_annotation(self):
        """白名单命中的工具直接通过，不看注解。"""
        profile = AgentProfile(
            name="default",
            description="default",
            soul="", agents_rules="", identity="",
            allowed_tools=["write_file"],
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("write_file", {"destructive": True})

        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.ALLOW
        assert decision.reason == "allowed"

    def test_accept_mode_destructive_still_asks(self):
        """B3: accept 模式下 destructive 工具仍 ASK，不一键放行。"""
        profile = AgentProfile(
            name="admin",
            description="admin",
            soul="", agents_rules="", identity="",
            permission_mode="accept",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("write_file", {"destructive": True})

        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.ASK

    def test_accept_mode_openworld_still_asks(self):
        """B3: accept 模式下 openWorld 工具仍 ASK。"""
        profile = AgentProfile(
            name="admin",
            description="admin",
            soul="", agents_rules="", identity="",
            permission_mode="accept",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("web_search", {"openWorld": True})

        decision = pipeline.check("web_search", {})
        assert decision.action == PermissionDecision.ASK

    def test_accept_mode_safe_tool_still_allows(self):
        """B3: accept 模式下无危险注解的工具仍 ALLOW（回归保护）。"""
        profile = AgentProfile(
            name="admin",
            description="admin",
            soul="", agents_rules="", identity="",
            permission_mode="accept",
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("read_file", {})  # 未注册注解
        assert decision.action == PermissionDecision.ALLOW


class TestEdgeCases:
    """PermissionPipeline 边界情况测试。"""

    def test_disallowed_overrides_allowed(self):
        """disallowed_tools 优先于 allowed_tools — 同一工具在两列表中被 DENY。"""
        profile = AgentProfile(
            name="conflict",
            description="冲突测试",
            soul="", agents_rules="", identity="",
            allowed_tools=["write_file"],
            disallowed_tools=["write_file"],
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.DENY
        assert decision.reason == "disallowed"

    def test_no_annotation_ask_mode_returns_low(self):
        """无注解的 unknown tool 在 ask 模式下返回 LOW ASK。"""
        profile = AgentProfile(
            name="default",
            description="默认",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)

        decision = pipeline.check("unknown_tool", {})
        assert decision.action == PermissionDecision.ASK
        assert decision.risk_level == RiskLevel.LOW
        assert decision.reason == "unknown"

    def test_empty_critical_tools_no_impact(self):
        """_CRITICAL_TOOLS 为空集合时不影响正常权限决策流程。"""
        profile = AgentProfile(
            name="default",
            description="默认",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("read_file", {"readOnly": True})

        decision = pipeline.check("read_file", {})
        assert decision.action == PermissionDecision.ALLOW
        assert decision.reason == "readOnly"

    def test_destructive_plus_idempotent_is_medium_ask(self):
        """destructive + idempotent 注解组合返回 MEDIUM ASK。"""
        profile = AgentProfile(
            name="default",
            description="默认",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        pipeline.register_annotations("upsert_record", {"destructive": True, "idempotent": True})

        decision = pipeline.check("upsert_record", {})
        assert decision.action == PermissionDecision.ASK
        assert decision.risk_level == RiskLevel.MEDIUM
        assert decision.reason == "destructive_idempotent"


class TestCriticalToolsConstructor:
    """PermissionPipeline critical_tools 构造器注入测试。"""

    def test_critical_tools_deny(self):
        """critical_tools 中的工具被 DENY。"""
        profile = AgentProfile(
            name="default",
            description="默认",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(
            profile=profile,
            critical_tools=frozenset({"rm", "execute_code"}),
        )
        decision = pipeline.check("rm", {})
        assert decision.action == PermissionDecision.DENY
        assert decision.reason == "critical"
        assert decision.risk_level == RiskLevel.CRITICAL

    def test_empty_critical_tools_passthrough(self):
        """critical_tools 为空时不拦截，走后续 profile disallowed 检查。"""
        profile = AgentProfile(
            name="default",
            description="默认",
            soul="", agents_rules="", identity="",
            disallowed_tools=["write_file"],
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(
            profile=profile,
            critical_tools=frozenset(),
        )
        decision = pipeline.check("write_file", {})
        assert decision.action == PermissionDecision.DENY
        assert decision.reason == "disallowed"

    def test_default_critical_tools_no_deny(self):
        """不传 critical_tools（默认 frozenset()）时不拒绝任何工具。"""
        profile = AgentProfile(
            name="default",
            description="默认",
            soul="", agents_rules="", identity="",
            permission_mode="ask",
        )
        pipeline = PermissionPipeline(profile=profile)
        decision = pipeline.check("rm", {})
        assert decision.action == PermissionDecision.ASK


class TestPermissionPipelineFromLoader:
    """PermissionPipeline.from_loader() factory method tests."""

    def _make_loader(
        self,
        profile: AgentProfile,
        settings: Settings | None = None,
    ) -> MagicMock:
        """Create a mock ConfigLoader that returns the given profile and settings."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = settings or Settings()
        # from_loader calls AgentProfile.from_profile(loader, name) internally
        # We need to mock it on the class, not on the loader
        return loader

    def test_from_loader_loads_profile(self):
        """from_loader() loads profile via AgentProfile.from_profile and creates pipeline."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = Settings()
        profile = AgentProfile(
            name="default",
            description="test",
            soul="", agents_rules="", identity="",
        )
        pipeline = PermissionPipeline.from_loader(loader, "default", _profile=profile)
        assert pipeline._profile.name == "default"

    def test_from_loader_injects_settings_allow(self):
        """from_loader() injects Settings.permissions.allow into profile's allowed_tools."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = Settings(
            permissions=PermissionsConfig(allow=["read_file", "list_files"]),
        )
        profile = AgentProfile(
            name="default",
            description="test",
            soul="", agents_rules="", identity="",
        )
        pipeline = PermissionPipeline.from_loader(loader, "default", _profile=profile)
        assert "read_file" in pipeline._profile.allowed_tools
        assert "list_files" in pipeline._profile.allowed_tools

    def test_from_loader_empty_settings_profile_tools_unchanged(self):
        """from_loader() with empty settings permissions, profile tools unchanged."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = Settings()
        profile = AgentProfile(
            name="default",
            description="test",
            soul="", agents_rules="", identity="",
            allowed_tools=["read_file"],
            disallowed_tools=["write_file"],
        )
        pipeline = PermissionPipeline.from_loader(loader, "default", _profile=profile)
        assert pipeline._profile.allowed_tools == ["read_file"]
        assert pipeline._profile.disallowed_tools == ["write_file"]

    def test_from_loader_settings_deny_added(self):
        """from_loader() with Settings deny list, denied tools are in disallowed_tools."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = Settings(
            permissions=PermissionsConfig(deny=["rm", "format_disk"]),
        )
        profile = AgentProfile(
            name="default",
            description="test",
            soul="", agents_rules="", identity="",
        )
        pipeline = PermissionPipeline.from_loader(loader, "default", _profile=profile)
        assert "rm" in pipeline._profile.disallowed_tools
        assert "format_disk" in pipeline._profile.disallowed_tools

    def test_from_loader_no_duplicate_allow(self):
        """from_loader() does not add duplicate entries to allowed_tools."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = Settings(
            permissions=PermissionsConfig(allow=["read_file"]),
        )
        profile = AgentProfile(
            name="default",
            description="test",
            soul="", agents_rules="", identity="",
            allowed_tools=["read_file"],
        )
        pipeline = PermissionPipeline.from_loader(loader, "default", _profile=profile)
        assert pipeline._profile.allowed_tools.count("read_file") == 1

    def test_from_loader_preserves_profile_mode(self):
        """from_loader() preserves the original profile's permission_mode."""
        loader = MagicMock(spec=ConfigLoader)
        loader.load_settings.return_value = Settings()
        profile = AgentProfile(
            name="admin",
            description="test",
            soul="", agents_rules="", identity="",
            permission_mode="accept",
        )
        pipeline = PermissionPipeline.from_loader(loader, "admin", _profile=profile)
        assert pipeline._profile.permission_mode == "accept"
