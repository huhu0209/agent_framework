"""PromptAssembler 单元测试 — 组装与渲染逻辑。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_framework.config.loader import ConfigLoader
from agent_framework.prompts.assembler import PromptAssembler, _BLOCK_TAGS
from agent_framework.prompts.profiles import AgentProfile


def _make_loader(tmp_path: Path) -> ConfigLoader:
    """创建无配置文件的 ConfigLoader（load_agents_md 和 load_rules 均返回空字符串）。"""
    return ConfigLoader(
        global_dir=tmp_path / "global",
        project_dir=tmp_path / "project",
    )


def _make_loader_with_agents_md(tmp_path: Path, content: str) -> ConfigLoader:
    """创建带 AGENTS.md 内容的 ConfigLoader。"""
    agents_md = tmp_path / "project" / ".agent-framework" / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text(content, encoding="utf-8")
    return ConfigLoader(
        global_dir=tmp_path / "global",
        project_dir=tmp_path / "project",
    )


def _make_profile(**overrides) -> AgentProfile:
    """创建最小 AgentProfile 实例。"""
    defaults = {"name": "test-agent", "description": "测试 Agent"}
    defaults.update(overrides)
    return AgentProfile(**defaults)


class TestPromptAssembler:
    """PromptAssembler.assemble() 基础测试。"""

    def test_assemble_empty_profile_returns_no_blocks(self, tmp_path: Path) -> None:
        """空 profile 返回空 block 列表。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        assert blocks == []

    def test_assemble_with_soul(self, tmp_path: Path) -> None:
        """soul 字段生成 SOUL block。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(soul="你是测试助手")
        blocks = assembler.assemble(loader, profile)
        soul_block = next(b for b in blocks if b.name == "SOUL")
        assert soul_block.content == "你是测试助手"
        assert soul_block.source == "injected"
        assert soul_block.stability == "static"
        assert soul_block.cache_breakpoint is True

    def test_assemble_with_agents_rules(self, tmp_path: Path) -> None:
        """agents_rules 字段生成 AGENTS_RULES block。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(agents_rules="遵守安全规则")
        blocks = assembler.assemble(loader, profile)
        rules_block = next(b for b in blocks if b.name == "AGENTS_RULES")
        assert rules_block.content == "遵守安全规则"
        assert rules_block.source == "injected"

    def test_assemble_with_identity(self, tmp_path: Path) -> None:
        """identity 字段生成 IDENTITY block。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(identity="我是 Agent-X")
        blocks = assembler.assemble(loader, profile)
        identity_block = next(b for b in blocks if b.name == "IDENTITY")
        assert identity_block.content == "我是 Agent-X"
        assert identity_block.stability == "semi_static"

    def test_assemble_user_context_not_separate_block(self, tmp_path: Path) -> None:
        """user_context 不再生成单独 block（由 ConfigLoader AGENTS.md 链替代）。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(user_context="用户上下文")
        blocks = assembler.assemble(loader, profile)
        block_names = [b.name for b in blocks]
        assert "USER" not in block_names
        assert "USER_PROVIDED" not in block_names

    def test_cache_breakpoints_set(self, tmp_path: Path) -> None:
        """SOUL、AGENTS_RULES、IDENTITY 设置 cache_breakpoint=True。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(
            soul="灵魂",
            agents_rules="规则",
            identity="身份",
            tool_guidance="工具指引",
        )
        blocks = assembler.assemble(loader, profile)
        for b in blocks:
            if b.name in ("SOUL", "AGENTS_RULES", "IDENTITY"):
                assert b.cache_breakpoint is True, f"{b.name} 应设 cache_breakpoint=True"
            elif b.name in ("SKILLS", "TOOL_GUIDANCE"):
                assert b.cache_breakpoint is False, f"{b.name} 应设 cache_breakpoint=False"

    def test_assemble_renders_to_string(self, tmp_path: Path) -> None:
        """render() 返回拼接后的字符串。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(soul="灵魂内容")
        result = assembler.render(loader, profile)
        assert "<soul>" in result
        assert "灵魂内容" in result
        assert "</soul>" in result

    def test_render_empty_profile(self, tmp_path: Path) -> None:
        """空 profile render 返回空字符串。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile()
        result = assembler.render(loader, profile)
        assert result == ""

    def test_block_order(self, tmp_path: Path) -> None:
        """block 顺序为 USER_PROVIDED -> RULES -> SOUL -> AGENTS_RULES -> IDENTITY -> SKILLS -> TOOL_GUIDANCE。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(
            soul="灵魂",
            agents_rules="规则",
            identity="身份",
            tool_guidance="工具",
        )
        blocks = assembler.assemble(loader, profile)
        names = [b.name for b in blocks]
        expected_order = ["SOUL", "AGENTS_RULES", "IDENTITY", "TOOL_GUIDANCE"]
        # 无 loader 内容时 USER_PROVIDED 和 RULES 不出现
        assert names == expected_order


class TestPromptAssemblerWithSkills:
    """PromptAssembler 与 SkillRegistry 集成测试。"""

    def _make_skill_registry(self) -> MagicMock:
        """创建模拟 SkillRegistry。"""
        registry = MagicMock()
        registry.describe_available.return_value = "skill-a: 技能A\nskill-b: 技能B"
        return registry

    def test_skills_block_present(self, tmp_path: Path) -> None:
        """有 SkillRegistry 时生成 SKILLS block。"""
        registry = self._make_skill_registry()
        assembler = PromptAssembler(skill_registry=registry)
        loader = _make_loader(tmp_path)
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        skills_block = next(b for b in blocks if b.name == "SKILLS")
        assert "skill-a" in skills_block.content
        assert skills_block.source == "auto_generated"

    def test_no_skills_block_without_registry(self, tmp_path: Path) -> None:
        """无 SkillRegistry 时不生成 SKILLS block。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        assert not any(b.name == "SKILLS" for b in blocks)

    def test_skills_block_not_cache_breakpoint(self, tmp_path: Path) -> None:
        """SKILLS block cache_breakpoint=False。"""
        registry = self._make_skill_registry()
        assembler = PromptAssembler(skill_registry=registry)
        loader = _make_loader(tmp_path)
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        skills_block = next(b for b in blocks if b.name == "SKILLS")
        assert skills_block.cache_breakpoint is False

    def test_skills_block_position(self, tmp_path: Path) -> None:
        """SKILLS block 在 TOOL_GUIDANCE 之前。"""
        registry = self._make_skill_registry()
        assembler = PromptAssembler(skill_registry=registry)
        loader = _make_loader(tmp_path)
        profile = _make_profile(
            soul="灵魂",
            tool_guidance="工具指引",
        )
        blocks = assembler.assemble(loader, profile)
        names = [b.name for b in blocks]
        skills_idx = names.index("SKILLS")
        tool_idx = names.index("TOOL_GUIDANCE")
        assert skills_idx < tool_idx


class TestRenderXmlTags:
    """render() XML 标签包装测试。"""

    def test_soul_wrapped_in_tag(self, tmp_path: Path) -> None:
        """soul 内容被 <soul> 标签包裹。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(soul="灵魂")
        result = assembler.render(loader, profile)
        assert "<soul>\n灵魂\n</soul>" in result

    def test_agents_rules_wrapped_in_instructions(self, tmp_path: Path) -> None:
        """agents_rules 被包装在 <instructions> 标签中。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(agents_rules="指令内容")
        result = assembler.render(loader, profile)
        assert "<instructions>\n指令内容\n</instructions>" in result

    def test_identity_wrapped_in_tag(self, tmp_path: Path) -> None:
        """identity 被包装在 <identity> 标签中。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(identity="身份")
        result = assembler.render(loader, profile)
        assert "<identity>\n身份\n</identity>" in result

    def test_tool_guidance_wrapped_in_tag(self, tmp_path: Path) -> None:
        """tool_guidance 被包装在 <tool-guidance> 标签中。"""
        assembler = PromptAssembler()
        loader = _make_loader(tmp_path)
        profile = _make_profile(tool_guidance="工具指引")
        result = assembler.render(loader, profile)
        assert "<tool-guidance>\n工具指引\n</tool-guidance>" in result

    def test_user_provided_wrapped_in_tag(self, tmp_path: Path) -> None:
        """USER_PROVIDED 内容被 <user-provided> 标签包裹（来自 ConfigLoader）。"""
        loader = _make_loader_with_agents_md(tmp_path, "用户指令内容")
        assembler = PromptAssembler()
        profile = _make_profile()
        result = assembler.render(loader, profile)
        assert "<user-provided>" in result
        assert "用户指令内容" in result
        assert "</user-provided>" in result

    def test_rules_wrapped_in_tag(self, tmp_path: Path) -> None:
        """RULES 内容被 <rules> 标签包裹。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "test.md").write_text("测试规则", encoding="utf-8")
        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile()
        result = assembler.render(loader, profile)
        assert "<rules>\n测试规则\n</rules>" in result

    def test_full_profile_all_tags_present(self, tmp_path: Path) -> None:
        """完整 profile 渲染包含所有预期标签。"""
        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile(
            soul="灵魂",
            agents_rules="规则",
            identity="身份",
            tool_guidance="工具",
        )
        result = assembler.render(loader, profile)
        assert "<soul>" in result
        assert "<instructions>" in result
        assert "<identity>" in result
        assert "<tool-guidance>" in result


class TestUserProvidedFromLoader:
    """USER_PROVIDED block 来自 ConfigLoader 的测试。"""

    def test_user_provided_block_from_loader(self, tmp_path: Path) -> None:
        """ConfigLoader 的 AGENTS.md 内容出现在 USER_PROVIDED block 中。"""
        loader = _make_loader_with_agents_md(tmp_path, "来自 AGENTS.md 的指令")
        assembler = PromptAssembler()
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        user_block = next(b for b in blocks if b.name == "USER_PROVIDED")
        assert "来自 AGENTS.md 的指令" in user_block.content
        assert user_block.source == "auto_generated"
        assert user_block.stability == "semi_static"
        assert user_block.cache_breakpoint is True

    def test_user_provided_empty_when_no_agents_md(self, tmp_path: Path) -> None:
        """无 AGENTS.md 时不生成 USER_PROVIDED block。"""
        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        assert not any(b.name == "USER_PROVIDED" for b in blocks)


class TestRulesBlockFromLoader:
    """RULES block 来自 RuleLoader 的测试。"""

    def test_rules_block_from_loader(self, tmp_path: Path) -> None:
        """RuleLoader 加载的规则内容出现在 RULES block 中。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "safety.md").write_text("安全规则内容", encoding="utf-8")
        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        rules_block = next(b for b in blocks if b.name == "RULES")
        assert "安全规则内容" in rules_block.content
        assert rules_block.source == "auto_generated"
        assert rules_block.stability == "semi_static"
        assert rules_block.cache_breakpoint is True

    def test_rules_empty_when_no_rules(self, tmp_path: Path) -> None:
        """无规则文件时不生成 RULES block。"""
        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile()
        blocks = assembler.assemble(loader, profile)
        assert not any(b.name == "RULES" for b in blocks)


class TestContextPathForwarding:
    """context_path 正确传递到 RuleLoader 的测试。"""

    def test_context_path_passed_to_rule_loader(self, tmp_path: Path) -> None:
        """context_path 传递给 RuleLoader，路径匹配的规则加载，不匹配的跳过。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "python_rule.md").write_text(
            "---\npaths: src/**.py\n---\nPython 规则",
            encoding="utf-8",
        )
        (rules_dir / "global_rule.md").write_text(
            "全局规则",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile()

        # 匹配 src/utils.py
        blocks = assembler.assemble(loader, profile, context_path="src/utils.py")
        rules_block = next(b for b in blocks if b.name == "RULES")
        assert "Python 规则" in rules_block.content
        assert "全局规则" in rules_block.content

    def test_context_path_non_matching_skips_scoped(self, tmp_path: Path) -> None:
        """context_path 不匹配时，限定规则不加载。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "python_rule.md").write_text(
            "---\npaths: src/**.py\n---\nPython 规则",
            encoding="utf-8",
        )
        (rules_dir / "global_rule.md").write_text(
            "全局规则",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        assembler = PromptAssembler()
        profile = _make_profile()

        # 不匹配 docs/readme.md
        blocks = assembler.assemble(loader, profile, context_path="docs/readme.md")
        rules_block = next(b for b in blocks if b.name == "RULES")
        assert "Python 规则" not in rules_block.content
        assert "全局规则" in rules_block.content
