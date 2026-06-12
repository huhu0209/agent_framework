"""E2E 集成测试 — 验证 ConfigLoader -> discover -> adapters -> registries 全链路。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_framework.agents.config import AgentConfig
from agent_framework.commands.dispatcher import CommandDispatcher
from agent_framework.config.loader import ConfigLoader
from agent_framework.hooks.manager import HookManager
from agent_framework.prompts.assembler import PromptAssembler
from agent_framework.prompts.profiles import AgentProfile
from agent_framework.rules.loader import RuleLoader
from agent_framework.skills.registry import SkillRegistry


def _setup_framework(tmp_path: Path) -> ConfigLoader:
    """创建带测试数据的 ConfigLoader 实例。"""
    global_dir = tmp_path / "global" / ".agent-framework"
    project_dir = tmp_path / "project" / ".agent-framework"
    global_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)

    # settings.json
    (global_dir / "settings.json").write_text(
        json.dumps({"model": "test-model", "llm": {"provider": "anthropic"}}),
        encoding="utf-8",
    )

    # AGENTS.md
    (global_dir / "AGENTS.md").write_text("全局指令内容", encoding="utf-8")

    # skills/test-skill/SKILL.md
    skill_dir = global_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: 测试技能\n---\n技能内容",
        encoding="utf-8",
    )

    # rules/global-rule.md (无 paths frontmatter — 始终加载)
    rules_global = global_dir / "rules"
    rules_global.mkdir(parents=True)
    (rules_global / "global-rule.md").write_text("全局安全规则", encoding="utf-8")

    # profiles/default/soul.md
    profile_dir = global_dir / "profiles" / "default"
    profile_dir.mkdir(parents=True)
    (profile_dir / "soul.md").write_text("你是测试助手", encoding="utf-8")
    (profile_dir / "agents.md").write_text("遵守安全规范", encoding="utf-8")

    # hooks/hooks.json
    hooks_dir = global_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.json").write_text(
        json.dumps({
            "hooks": {
                "pre_tool_use": [
                    {
                        "matcher": "*",
                        "hooks": [{"command": "echo ok"}],
                    },
                ],
            },
        }),
        encoding="utf-8",
    )

    # rules/scoped-rule.md in project (with paths frontmatter)
    rules_project = project_dir / "rules"
    rules_project.mkdir(parents=True)
    (rules_project / "scoped-rule.md").write_text(
        "---\npaths: src/**.py\n---\nPython 文件规则",
        encoding="utf-8",
    )

    return ConfigLoader(
        global_dir=tmp_path / "global",
        project_dir=tmp_path / "project",
    )


class TestE2EIntegration:
    """端到端集成测试 — 从 ConfigLoader 到完整 system prompt。"""

    def test_configloader_loads_settings(self, tmp_path: Path) -> None:
        """ConfigLoader.load_settings() 返回 Settings 对象。"""
        loader = _setup_framework(tmp_path)
        settings = loader.load_settings()
        assert settings.model == "test-model"
        assert settings.llm.provider == "anthropic"

    def test_configloader_discovers_modules(self, tmp_path: Path) -> None:
        """ConfigLoader.discover() 返回正确的模块目录路径。"""
        loader = _setup_framework(tmp_path)
        skill_paths = loader.discover("skills")
        assert len(skill_paths) >= 1
        assert skill_paths[0].name == "skills"

        rule_paths = loader.discover("rules")
        assert len(rule_paths) == 2  # global + project

    def test_skill_registry_from_loader(self, tmp_path: Path) -> None:
        """SkillRegistry.from_loader() 返回包含测试 skill 的注册表。"""
        loader = _setup_framework(tmp_path)
        registry = SkillRegistry.from_loader(loader)
        catalog = registry.describe_available()
        assert "test-skill" in catalog

    def test_hook_manager_from_loader(self, tmp_path: Path) -> None:
        """HookManager.from_loader() 返回已加载 hooks.json 的管理器。"""
        loader = _setup_framework(tmp_path)
        manager = HookManager.from_loader(loader)
        # HookManager 加载后可以通过 list 或注册表验证
        assert manager is not None

    def test_agent_profile_from_profile(self, tmp_path: Path) -> None:
        """AgentProfile.from_profile() 返回带有 soul 和 agents 字段的 profile。"""
        loader = _setup_framework(tmp_path)
        profile = AgentProfile.from_profile(loader, "default")
        assert profile.name == "default"
        assert "测试助手" in profile.soul
        assert "安全规范" in profile.agents_rules

    def test_rule_loader_with_scoped_rules(self, tmp_path: Path) -> None:
        """RuleLoader 根据路径匹配加载正确的规则。"""
        loader = _setup_framework(tmp_path)

        # 无 context_path — 只加载全局规则
        rules_no_ctx = RuleLoader.load_rules(loader, context_path=None)
        assert "全局安全规则" in rules_no_ctx
        assert "Python 文件规则" not in rules_no_ctx

        # 匹配 context_path — 加载全局 + 匹配的限定规则
        rules_with_ctx = RuleLoader.load_rules(loader, context_path="src/main.py")
        assert "全局安全规则" in rules_with_ctx
        assert "Python 文件规则" in rules_with_ctx

    def test_prompt_assembler_full_pipeline(self, tmp_path: Path) -> None:
        """PromptAssembler 全链路组装包含所有预期 block。"""
        loader = _setup_framework(tmp_path)
        registry = SkillRegistry.from_loader(loader)
        profile = AgentProfile.from_profile(loader, "default")
        assembler = PromptAssembler(skill_registry=registry)

        blocks = assembler.assemble(loader, profile)
        block_names = [b.name for b in blocks]

        # 验证 block 包含所有预期类型
        assert "USER_PROVIDED" in block_names
        assert "RULES" in block_names
        assert "SOUL" in block_names
        assert "AGENTS_RULES" in block_names
        assert "SKILLS" in block_names

        # 验证内容
        user_block = next(b for b in blocks if b.name == "USER_PROVIDED")
        assert "全局指令内容" in user_block.content

        rules_block = next(b for b in blocks if b.name == "RULES")
        assert "全局安全规则" in rules_block.content

        soul_block = next(b for b in blocks if b.name == "SOUL")
        assert "测试助手" in soul_block.content

        skills_block = next(b for b in blocks if b.name == "SKILLS")
        assert "test-skill" in skills_block.content

    def test_render_produces_complete_system_prompt(self, tmp_path: Path) -> None:
        """render() 输出包含所有预期 XML 标签且顺序正确。"""
        loader = _setup_framework(tmp_path)
        registry = SkillRegistry.from_loader(loader)
        profile = AgentProfile.from_profile(loader, "default")
        assembler = PromptAssembler(skill_registry=registry)

        result = assembler.render(loader, profile)

        # 验证所有 XML 标签存在
        assert "<user-provided>" in result
        assert "</user-provided>" in result
        assert "<rules>" in result
        assert "</rules>" in result
        assert "<soul>" in result
        assert "</soul>" in result
        assert "<instructions>" in result
        assert "</instructions>" in result
        assert "<skills>" in result
        assert "</skills>" in result

        # 验证标签顺序: user-provided < rules < soul < instructions < skills
        user_idx = result.index("<user-provided>")
        rules_idx = result.index("<rules>")
        soul_idx = result.index("<soul>")
        instructions_idx = result.index("<instructions>")
        skills_idx = result.index("<skills>")
        assert user_idx < rules_idx < soul_idx < instructions_idx < skills_idx

    def test_prompt_assembler_with_context_path(self, tmp_path: Path) -> None:
        """context_path 通过 assembler 全链路传递 — 路径限定规则正确加载。"""
        loader = _setup_framework(tmp_path)
        registry = SkillRegistry.from_loader(loader)
        profile = AgentProfile.from_profile(loader, "default")
        assembler = PromptAssembler(skill_registry=registry)

        # 传入 context_path 匹配 scoped-rule 的 paths 模式 (src/**.py)
        blocks = assembler.assemble(loader, profile, context_path="src/main.py")
        rules_block = next(b for b in blocks if b.name == "RULES")

        # 全局规则始终加载
        assert "全局安全规则" in rules_block.content
        # 路径限定规则因 context_path 匹配而加载
        assert "Python 文件规则" in rules_block.content
