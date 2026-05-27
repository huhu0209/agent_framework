"""CommandRouter 测试。"""

import pytest

from agent_framework.commands.router import CommandRouter
from agent_framework.commands.types import CommandSource
from agent_framework.skills.registry import SkillRegistry

from tests.helpers import create_skill


class TestNonCommandInput:
    def test_plain_text(self):
        router = CommandRouter()
        result = router.resolve("hello world")
        assert result.is_command is False
        assert result.content == "hello world"

    def test_slash_only(self):
        router = CommandRouter()
        result = router.resolve("/")
        assert result.is_command is False
        assert result.content == "/"

    def test_double_slash(self):
        router = CommandRouter()
        result = router.resolve("//")
        assert result.is_command is False
        assert result.content == "//"

    def test_unknown_command_no_registry(self):
        router = CommandRouter()
        result = router.resolve("/unknown")
        assert result.is_command is False
        assert result.content == "/unknown"


class TestHelpBuiltin:
    def test_help_lists_builtins(self):
        router = CommandRouter()
        result = router.resolve("/help")
        assert result.is_command is True
        assert result.skill_loaded is False
        assert result.source == CommandSource.BUILTIN
        assert "/help" in result.content

    def test_help_lists_user_invocable_skills(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用", "body")
        create_skill(skills_dir, "internal", "内部", "body", **{"user-invocable": "false"})

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/help")

        assert result.is_command is True
        assert "/deploy" in result.content
        assert "/internal" not in result.content

    def test_help_ignores_args(self):
        router = CommandRouter()
        result = router.resolve("/help something")
        assert result.is_command is True
        assert "/help" in result.content

    def test_help_builtin_and_skill_alignment(self, tmp_path):
        """builtins 和 skills 的描述列对齐一致。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用", "body")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/help")

        lines = result.content.split("\n")
        help_line = next(l for l in lines if "/help" in l)
        deploy_line = next(l for l in lines if "/deploy" in l)

        help_desc_idx = help_line.index("显示所有可用命令")
        deploy_desc_idx = deploy_line.index("部署应用")
        assert help_desc_idx == deploy_desc_idx, \
            f"help 描述在列 {help_desc_idx}, deploy 描述在列 {deploy_desc_idx}"


class TestSkillLoading:
    def test_existing_skill(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署", "执行部署: $ARGUMENTS")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/deploy --env prod")

        assert result.is_command is True
        assert result.skill_loaded is True
        assert result.source == CommandSource.SKILL
        assert "--env prod" in result.content
        assert "$ARGUMENTS" not in result.content

    def test_skill_no_args_empty_replacement(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "review", "审查", "参数: [$ARGUMENTS]")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/review")

        assert result.is_command is True
        assert "参数: []" in result.content

    def test_nonexistent_skill_falls_through(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/nope")

        assert result.is_command is False
        assert result.content == "/nope"

    def test_user_invocable_false_falls_through(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "internal", "内部", "body", **{"user-invocable": "false"})

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/internal")

        assert result.is_command is False
        assert result.content == "/internal"

    def test_skill_load_error_falls_through(self):
        """skill manifest 存在但 load_full_text 返回错误时降级。"""
        from unittest.mock import MagicMock
        from agent_framework.skills.registry import SkillLoadResult

        registry = MagicMock(spec=SkillRegistry)
        manifest = MagicMock()
        manifest.user_invocable = True
        registry.get_manifest.return_value = manifest
        registry.load_full_text.return_value = SkillLoadResult(
            content="加载失败", is_error=True
        )

        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/broken")
        assert result.is_command is False
        assert result.content == "/broken"

    def test_multiple_arguments_placeholder(self, tmp_path):
        """多个 $ARGUMENTS 占位符均被替换为相同值。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "wrap", "包装", "前: $ARGUMENTS | 后: $ARGUMENTS")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/wrap hello")

        assert result.is_command is True
        assert "前: hello | 后: hello" in result.content
        assert "$ARGUMENTS" not in result.content

    def test_load_error_logs_debug_message(self, caplog):
        """skill 加载失败时记录 debug 日志。"""
        import logging
        from unittest.mock import MagicMock
        from agent_framework.skills.registry import SkillLoadResult

        registry = MagicMock(spec=SkillRegistry)
        manifest = MagicMock()
        manifest.user_invocable = True
        registry.get_manifest.return_value = manifest
        registry.load_full_text.return_value = SkillLoadResult(
            content="磁盘读取失败", is_error=True
        )

        router = CommandRouter(skill_registry=registry)
        with caplog.at_level(logging.DEBUG, logger="agent_framework.commands.router"):
            router.resolve("/broken")

        assert any("broken" in r.message and "加载失败" in r.message for r in caplog.records)


class TestEdgeCases:
    def test_builtin_priority_over_skill(self, tmp_path):
        """同名时 builtin 优先于 skill。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "help", "帮助 skill", "skill help body")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/help")

        assert result.is_command is True
        assert result.source == CommandSource.BUILTIN
        assert result.skill_loaded is False

    def test_whitespace_in_args(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "search", "搜索", "查找: $ARGUMENTS")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/search   hello   world  ")

        assert result.is_command is True
        assert "hello   world" in result.content

    def test_skill_body_without_arguments_placeholder(self, tmp_path):
        """skill 正文没有 $ARGUMENTS 时正常加载，不做替换。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "status", "状态", "系统运行正常")

        registry = SkillRegistry([skills_dir])
        router = CommandRouter(skill_registry=registry)
        result = router.resolve("/status --verbose")

        assert result.is_command is True
        assert "系统运行正常" in result.content

    def test_no_registry_unknown_command(self):
        """无 registry 时，未知命令直接降级。"""
        router = CommandRouter()
        result = router.resolve("/deploy")
        assert result.is_command is False
        assert result.content == "/deploy"

    def test_builtin_without_handler(self):
        """builtin handler 为 None 时仍返回 is_command=True。"""
        from agent_framework.commands.types import SlashCommand, CommandSource
        router = CommandRouter()
        router._builtins["noop"] = SlashCommand(
            name="noop", description="无操作", source=CommandSource.BUILTIN
        )
        result = router.resolve("/noop")
        assert result.is_command is True
        assert result.content == "/noop"
        assert result.source == CommandSource.BUILTIN
