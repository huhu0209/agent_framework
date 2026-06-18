"""AgentProfile 和 PromptBlock 测试。"""

import logging
from pathlib import Path

import pytest

from agent_framework.config.loader import ConfigLoader
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


# ---------------------------------------------------------------------------
# AgentProfile.from_profile
# ---------------------------------------------------------------------------

class TestAgentProfileFromProfile:
    """AgentProfile.from_profile(loader, name) factory method tests."""

    def _setup_profile_dir(
        self, base: Path, profile_name: str,
        soul: str = "", agents: str = "", identity: str = "",
        tool_guidance: str = "",
    ) -> Path:
        """Helper: create a profile directory under base/.agent-framework/profiles/name."""
        profile_dir = base / ".agent-framework" / "profiles" / profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        if soul:
            (profile_dir / "soul.md").write_text(soul, encoding="utf-8")
        if agents:
            (profile_dir / "agents.md").write_text(agents, encoding="utf-8")
        if identity:
            (profile_dir / "identity.md").write_text(identity, encoding="utf-8")
        if tool_guidance:
            (profile_dir / "tool_guidance.md").write_text(tool_guidance, encoding="utf-8")
        return profile_dir

    def test_from_profile_no_dirs_raises(self):
        """No profile dirs exist => load_profile returns empty dict => should raise."""
        loader = ConfigLoader(global_dir=Path("/nonexistent"), project_dir=Path("/nonexistent"))
        # load_profile returns {} when no dirs exist, so from_profile should raise
        with pytest.raises(Exception):
            AgentProfile.from_profile(loader, "nonexistent")

    def test_from_profile_global_only(self, tmp_path: Path):
        """Only global profile directory exists => returns profile with merged fields."""
        self._setup_profile_dir(
            tmp_path / "global", "coder",
            soul="Global soul", agents="Global rules", identity="Global identity",
        )

        loader = ConfigLoader(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
        )
        profile = AgentProfile.from_profile(loader, "coder")

        assert isinstance(profile, AgentProfile)
        assert profile.name == "coder"
        assert profile.soul == "Global soul"
        assert profile.agents_rules == "Global rules"
        assert profile.identity == "Global identity"

    def test_from_profile_project_overrides_global(self, tmp_path: Path):
        """Global + project => project non-empty fields override global."""
        self._setup_profile_dir(
            tmp_path / "global", "dev",
            soul="Global soul", agents="Global rules",
        )
        self._setup_profile_dir(
            tmp_path / "project", "dev",
            soul="Project soul",
        )

        loader = ConfigLoader(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
        )
        profile = AgentProfile.from_profile(loader, "dev")

        assert profile.soul == "Project soul"
        assert profile.agents_rules == "Global rules"  # project didn't override

    def test_from_profile_returns_correct_instance(self, tmp_path: Path):
        """Returns valid AgentProfile instance with all field mappings."""
        self._setup_profile_dir(
            tmp_path / "global", "full",
            soul="Soul text", agents="Agents rules",
            identity="Identity text", tool_guidance="Tool guidance",
        )

        loader = ConfigLoader(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
        )
        profile = AgentProfile.from_profile(loader, "full")

        assert profile.name == "full"
        assert profile.soul == "Soul text"
        assert profile.agents_rules == "Agents rules"
        assert profile.identity == "Identity text"
        assert profile.tool_guidance == "Tool guidance"
        assert profile.permission_mode == "ask"

    def test_from_profile_missing_files_default_values(self, tmp_path: Path):
        """Missing sub-files produce empty/default values."""
        # Only create soul.md, skip others
        profile_dir = tmp_path / "global" / ".agent-framework" / "profiles" / "minimal"
        profile_dir.mkdir(parents=True)
        (profile_dir / "soul.md").write_text("Minimal soul", encoding="utf-8")

        loader = ConfigLoader(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
        )
        profile = AgentProfile.from_profile(loader, "minimal")

        assert profile.soul == "Minimal soul"
        assert profile.agents_rules == ""
        assert profile.identity == ""
        assert profile.tool_guidance is None
