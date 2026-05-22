"""AgentProfile 和 PromptBlock 测试。"""

from pathlib import Path

import pytest

from agent_framework.prompts.profiles import AgentProfile, PromptBlock


class TestAgentProfile:
    def test_create_profile(self):
        profile = AgentProfile(
            name="coder",
            description="代码生成专家",
            soul="你是一个简洁的工程师。",
            agents_rules="先读再改。改完跑测试。",
            identity="你是用户的编程搭档。",
        )
        assert profile.name == "coder"
        assert profile.permission_mode == "ask"
        assert profile.tool_guidance is None

    def test_from_directory(self, tmp_path: Path):
        profile_dir = tmp_path / "coder"
        profile_dir.mkdir()
        (profile_dir / "soul.md").write_text("简洁工程师。", encoding="utf-8")
        (profile_dir / "agents.md").write_text("先读再改。", encoding="utf-8")
        (profile_dir / "identity.md").write_text("编程搭档。", encoding="utf-8")

        profile = AgentProfile.from_directory(profile_dir)
        assert profile.name == "coder"
        assert "简洁" in profile.soul

    def test_from_directory_missing_files(self, tmp_path: Path):
        profile_dir = tmp_path / "empty"
        profile_dir.mkdir()

        profile = AgentProfile.from_directory(profile_dir)
        assert profile.soul == ""
        assert profile.name == "empty"

    def test_from_directory_with_tool_guidance(self, tmp_path: Path):
        profile_dir = tmp_path / "coder"
        profile_dir.mkdir()
        (profile_dir / "soul.md").write_text("soul", encoding="utf-8")
        (profile_dir / "agents.md").write_text("rules", encoding="utf-8")
        (profile_dir / "identity.md").write_text("id", encoding="utf-8")
        (profile_dir / "tool_guidance.md").write_text("grep 先搜再读", encoding="utf-8")

        profile = AgentProfile.from_directory(profile_dir)
        assert profile.tool_guidance == "grep 先搜再读"


class TestPromptBlock:
    def test_create_block(self):
        block = PromptBlock(
            name="SOUL",
            content="你是一个助手。",
            source="injected",
            stability="static",
            cache_breakpoint=True,
        )
        assert block.name == "SOUL"
        assert block.cache_breakpoint is True

    def test_block_stability_values(self):
        for stability in ("static", "semi_static", "dynamic"):
            block = PromptBlock(
                name="test", content="x", source="injected",
                stability=stability, cache_breakpoint=False,
            )
            assert block.stability == stability
