"""CommandDispatcher 测试。"""

import logging
from unittest.mock import MagicMock

import pytest

from agent_framework.commands.dispatcher import CommandDispatcher
from agent_framework.commands.types import CommandAction, CommandCategory, SlashCommand
from agent_framework.skills.registry import SkillLoadResult, SkillRegistry

from tests.helpers import create_skill


class TestNonCommandInput:
    def test_plain_text(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("hello world")
        assert result.action == CommandAction.NONE
        assert result.message == "hello world"

    def test_slash_only(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/")
        assert result.action == CommandAction.NONE
        assert result.message == "/"

    def test_double_slash(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("//")
        assert result.action == CommandAction.NONE

    def test_unknown_command_no_registry(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/unknown")
        assert result.action == CommandAction.NONE
        assert result.message == "/unknown"


class TestHelpBuiltin:
    def test_help_action(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/help")
        assert result.action == CommandAction.SHOW_HELP
        assert "/help" in result.message

    def test_help_lists_skills(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用", "body")
        create_skill(skills_dir, "internal", "内部", "body", **{"user-invocable": "false"})

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/help")

        assert result.action == CommandAction.SHOW_HELP
        assert "/deploy" in result.message
        assert "/internal" not in result.message

    def test_help_lists_builtins(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/help")
        assert "/clear" in result.message
        assert "/status" in result.message
        assert "/compact" in result.message
        assert "/config" in result.message

    def test_help_ignores_args(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/help something")
        assert result.action == CommandAction.SHOW_HELP
        assert "/help" in result.message

    def test_help_builtin_and_skill_alignment(self, tmp_path):
        """builtins 和 skills 的描述列对齐一致。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用", "body")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/help")

        lines = result.message.split("\n")
        help_line = next(l for l in lines if "/help" in l)
        deploy_line = next(l for l in lines if "/deploy" in l)

        help_desc_idx = help_line.index("显示所有可用命令")
        deploy_desc_idx = deploy_line.index("部署应用")
        assert help_desc_idx == deploy_desc_idx, (
            f"help 描述在列 {help_desc_idx}, deploy 描述在列 {deploy_desc_idx}"
        )

    def test_help_ignores_inactive_skills(self, tmp_path):
        """paths 激活的 skill 在未激活时不显示在 help 中。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "auto"
        skill_path.mkdir()
        meta = "---\nname: auto\ndescription: 自动激活\npaths: \"src/**/*.py\"\n---\nbody"
        (skill_path / "SKILL.md").write_text(meta, encoding="utf-8")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/help")

        assert "/auto" not in result.message


class TestClearBuiltin:
    def test_clear_action(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/clear")
        assert result.action == CommandAction.CLEAR_CONTEXT

    def test_clear_ignores_args(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/clear all")
        assert result.action == CommandAction.CLEAR_CONTEXT


class TestCompactBuiltin:
    def test_compact_action(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/compact")
        assert result.action == CommandAction.COMPACT_CONTEXT

    def test_compact_ignores_args(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/compact deep")
        assert result.action == CommandAction.COMPACT_CONTEXT


class TestStatusBuiltin:
    def test_status_action(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/status")
        assert result.action == CommandAction.SHOW_STATUS

    def test_status_ignores_args(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/status --verbose")
        assert result.action == CommandAction.SHOW_STATUS


class TestConfigBuiltin:
    def test_config_view(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/config")
        assert result.action == CommandAction.SET_CONFIG

    def test_config_set(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/config model claude-haiku-4-5")
        assert result.action == CommandAction.SET_CONFIG
        assert "claude-haiku-4-5" in result.message
        assert result.data == {"model": "claude-haiku-4-5"}

    def test_config_single_key(self):
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/config model")
        assert result.action == CommandAction.SET_CONFIG
        assert "model" in result.message


class TestSkillLoading:
    def test_existing_skill(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署", "执行部署: $ARGUMENTS")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/deploy --env prod")

        assert result.action == CommandAction.LOAD_SKILL
        assert "--env prod" in result.skill_content
        assert "$ARGUMENTS" not in result.skill_content

    def test_skill_no_args_empty_replacement(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "review", "审查", "参数: [$ARGUMENTS]")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/review")

        assert result.action == CommandAction.LOAD_SKILL
        assert "参数: []" in result.skill_content

    def test_nonexistent_skill_falls_through(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/nope")
        assert result.action == CommandAction.NONE
        assert result.message == "/nope"

    def test_user_invocable_false_falls_through(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "internal", "内部", "body", **{"user-invocable": "false"})

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/internal")
        assert result.action == CommandAction.NONE

    def test_skill_load_error_falls_through(self):
        """skill manifest 存在但 load_full_text 返回错误时降级。"""
        registry = MagicMock(spec=SkillRegistry)
        manifest = MagicMock()
        manifest.user_invocable = True
        registry.get_manifest.return_value = manifest
        registry.load_full_text.return_value = SkillLoadResult(
            content="加载失败", is_error=True
        )

        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/broken")
        assert result.action == CommandAction.NONE
        assert result.message == "/broken"

    def test_multiple_arguments_placeholder(self, tmp_path):
        """多个 $ARGUMENTS 占位符均被替换为相同值。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "wrap", "包装", "前: $ARGUMENTS | 后: $ARGUMENTS")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/wrap hello")

        assert result.action == CommandAction.LOAD_SKILL
        assert "前: hello | 后: hello" in result.skill_content
        assert "$ARGUMENTS" not in result.skill_content

    def test_load_error_logs_debug_message(self, caplog):
        """skill 加载失败时记录 debug 日志。"""
        registry = MagicMock(spec=SkillRegistry)
        manifest = MagicMock()
        manifest.user_invocable = True
        registry.get_manifest.return_value = manifest
        registry.load_full_text.return_value = SkillLoadResult(
            content="磁盘读取失败", is_error=True
        )

        dispatcher = CommandDispatcher(skill_registry=registry)
        with caplog.at_level(logging.DEBUG, logger="agent_framework.commands.dispatcher"):
            dispatcher.resolve("/broken")

        assert any("broken" in r.message and "加载失败" in r.message for r in caplog.records)

    def test_skill_body_without_arguments_placeholder(self, tmp_path):
        """skill 正文没有 $ARGUMENTS 时正常加载，不做替换。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "ping", "状态", "系统运行正常")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/ping --verbose")

        assert result.action == CommandAction.LOAD_SKILL
        assert "系统运行正常" in result.skill_content


class TestPriority:
    def test_builtin_priority_over_skill(self, tmp_path):
        """同名时 builtin 优先于 skill。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "help", "帮助 skill", "skill help body")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/help")

        assert result.action == CommandAction.SHOW_HELP
        assert result.skill_content == ""

    def test_no_registry_unknown_command(self):
        """无 registry 时，未知命令直接降级。"""
        dispatcher = CommandDispatcher()
        result = dispatcher.resolve("/deploy")
        assert result.action == CommandAction.NONE
        assert result.message == "/deploy"

    def test_builtin_without_handler(self):
        """builtin handler 为 None 时返回 NONE action。"""
        dispatcher = CommandDispatcher()
        dispatcher._builtins["noop"] = SlashCommand(
            name="noop", description="无操作", category=CommandCategory.QUERY
        )
        result = dispatcher.resolve("/noop")
        assert result.action == CommandAction.NONE
        assert result.message == "/noop"

    def test_whitespace_in_args(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "search", "搜索", "查找: $ARGUMENTS")

        registry = SkillRegistry([skills_dir])
        dispatcher = CommandDispatcher(skill_registry=registry)
        result = dispatcher.resolve("/search   hello   world  ")

        assert result.action == CommandAction.LOAD_SKILL
        assert "hello   world" in result.skill_content
