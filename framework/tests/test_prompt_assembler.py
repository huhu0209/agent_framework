"""PromptAssembler 测试。"""

from agent_framework.prompts.assembler import PromptAssembler
from agent_framework.prompts.profiles import AgentProfile


class TestPromptAssembler:
    def test_assemble_basic_profile(self):
        profile = AgentProfile(
            name="coder",
            description="test",
            soul="你是一个工程师。",
            agents_rules="先读再改。",
            identity="编程搭档。",
        )
        assembler = PromptAssembler()
        blocks = assembler.assemble(profile=profile)

        assert len(blocks) >= 3

        names = [b.name for b in blocks]
        assert "SOUL" in names
        assert "AGENTS_RULES" in names
        assert "IDENTITY" in names

    def test_assemble_with_tool_guidance(self):
        profile = AgentProfile(
            name="coder",
            description="test",
            soul="soul",
            agents_rules="rules",
            identity="identity",
            tool_guidance="grep 先搜再读。",
        )
        assembler = PromptAssembler()
        blocks = assembler.assemble(profile=profile)

        names = [b.name for b in blocks]
        assert "TOOL_GUIDANCE" in names

    def test_assemble_without_tool_guidance(self):
        profile = AgentProfile(
            name="coder",
            description="test",
            soul="soul",
            agents_rules="rules",
            identity="identity",
        )
        assembler = PromptAssembler()
        blocks = assembler.assemble(profile=profile)

        names = [b.name for b in blocks]
        assert "TOOL_GUIDANCE" not in names

    def test_assemble_with_user_context(self):
        profile = AgentProfile(
            name="coder",
            description="test",
            soul="soul",
            agents_rules="rules",
            identity="identity",
            user_context="用户偏好简洁回复。",
        )
        assembler = PromptAssembler()
        blocks = assembler.assemble(profile=profile)

        names = [b.name for b in blocks]
        assert "USER" in names

    def test_assemble_renders_to_string(self):
        profile = AgentProfile(
            name="coder",
            description="test",
            soul="你是一个工程师。",
            agents_rules="先读再改。",
            identity="编程搭档。",
        )
        assembler = PromptAssembler()
        text = assembler.render(profile=profile)

        assert "你是一个工程师" in text
        assert "先读再改" in text
        assert "编程搭档" in text

    def test_render_empty_profile(self):
        profile = AgentProfile(name="empty", description="test")
        assembler = PromptAssembler()
        text = assembler.render(profile=profile)

        assert text == ""

    def test_cache_breakpoints_set(self):
        profile = AgentProfile(
            name="coder",
            description="test",
            soul="soul",
            agents_rules="rules",
            identity="identity",
        )
        assembler = PromptAssembler()
        blocks = assembler.assemble(profile=profile)

        soul_block = next(b for b in blocks if b.name == "SOUL")
        assert soul_block.cache_breakpoint is True
        identity_block = next(b for b in blocks if b.name == "IDENTITY")
        assert identity_block.cache_breakpoint is True


from pathlib import Path
from agent_framework.skills.registry import SkillRegistry


class TestPromptAssemblerWithSkills:
    def _make_registry(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "deploy"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: deploy\ndescription: 部署\n---\nbody", encoding="utf-8"
        )
        return SkillRegistry([skills_dir])

    def test_no_skills_no_block(self):
        profile = AgentProfile(name="t", description="t", soul="soul")
        assembler = PromptAssembler()
        blocks = assembler.assemble(profile=profile)
        names = [b.name for b in blocks]
        assert "SKILLS" not in names

    def test_skills_block_injected(self, tmp_path):
        registry = self._make_registry(tmp_path)
        profile = AgentProfile(
            name="t", description="t", soul="soul", tool_guidance="guidance"
        )
        assembler = PromptAssembler(skill_registry=registry)
        blocks = assembler.assemble(profile=profile)
        names = [b.name for b in blocks]
        assert "SKILLS" in names

    def test_skills_block_position(self, tmp_path):
        """SKILLS 在 USER 和 TOOL_GUIDANCE 之间。"""
        registry = self._make_registry(tmp_path)
        profile = AgentProfile(
            name="t",
            description="t",
            soul="soul",
            user_context="user info",
            tool_guidance="guidance",
        )
        assembler = PromptAssembler(skill_registry=registry)
        blocks = assembler.assemble(profile=profile)
        names = [b.name for b in blocks]
        skills_idx = names.index("SKILLS")
        tool_idx = names.index("TOOL_GUIDANCE")
        assert skills_idx < tool_idx

    def test_render_includes_skills_catalog(self, tmp_path):
        registry = self._make_registry(tmp_path)
        profile = AgentProfile(name="t", description="t", soul="soul")
        assembler = PromptAssembler(skill_registry=registry)
        text = assembler.render(profile=profile)
        assert "deploy" in text


class TestRenderXmlTags:
    """render() XML tag wrapping — per D-07, D-09."""

    def test_soul_wrapped_in_xml(self):
        profile = AgentProfile(
            name="t", description="t", soul="你是一个工程师。"
        )
        text = PromptAssembler().render(profile=profile)
        assert "<soul>" in text
        assert "</soul>" in text
        assert "<soul>\n你是一个工程师。\n</soul>" in text

    def test_agents_rules_wrapped_in_instructions(self):
        profile = AgentProfile(
            name="t", description="t", agents_rules="先读再改。"
        )
        text = PromptAssembler().render(profile=profile)
        assert "<instructions>" in text
        assert "</instructions>" in text

    def test_identity_wrapped_in_xml(self):
        profile = AgentProfile(
            name="t", description="t", identity="编程搭档。"
        )
        text = PromptAssembler().render(profile=profile)
        assert "<identity>" in text
        assert "</identity>" in text

    def test_user_context_wrapped_in_user_provided(self):
        profile = AgentProfile(
            name="t", description="t", soul="s", user_context="用户偏好简洁回复。"
        )
        text = PromptAssembler().render(profile=profile)
        assert "<user-provided>" in text
        assert "</user-provided>" in text
        assert "<user-provided>\n用户偏好简洁回复。\n</user-provided>" in text

    def test_skills_wrapped_in_xml(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "deploy"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: deploy\ndescription: 部署\n---\nbody", encoding="utf-8"
        )
        from agent_framework.skills.registry import SkillRegistry

        registry = SkillRegistry([skills_dir])
        profile = AgentProfile(name="t", description="t", soul="soul")
        text = PromptAssembler(skill_registry=registry).render(profile=profile)
        assert "<skills>" in text
        assert "</skills>" in text

    def test_tool_guidance_wrapped_in_xml(self):
        profile = AgentProfile(
            name="t", description="t", soul="s", tool_guidance="grep 先搜再读。"
        )
        text = PromptAssembler().render(profile=profile)
        assert "<tool-guidance>" in text
        assert "</tool-guidance>" in text

    def test_render_empty_profile_no_tags(self):
        profile = AgentProfile(name="empty", description="test")
        text = PromptAssembler().render(profile=profile)
        assert text == ""

    def test_assemble_returns_raw_blocks_no_xml(self):
        """assemble() must NOT include XML wrapping — that's render()'s job."""
        profile = AgentProfile(
            name="t", description="t", soul="soul content"
        )
        blocks = PromptAssembler().assemble(profile=profile)
        for b in blocks:
            assert "<soul>" not in b.content
            assert "</soul>" not in b.content

    def test_full_profile_all_tags_present(self):
        profile = AgentProfile(
            name="t",
            description="t",
            soul="soul",
            agents_rules="rules",
            identity="identity",
            user_context="user info",
            tool_guidance="guidance",
        )
        text = PromptAssembler().render(profile=profile)
        assert "<soul>" in text
        assert "<instructions>" in text
        assert "<identity>" in text
        assert "<user-provided>" in text
        assert "<tool-guidance>" in text
