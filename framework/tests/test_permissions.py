"""权限管道测试。"""

import pytest

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
