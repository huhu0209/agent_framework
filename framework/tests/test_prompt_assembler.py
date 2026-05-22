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
