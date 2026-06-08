"""commands/types.py 类型定义测试。"""

import pytest

from agent_framework.commands.types import (
    CommandAction,
    CommandCategory,
    CommandResult,
    SlashCommand,
)


class TestCommandCategory:
    def test_values(self):
        assert CommandCategory.SESSION == "session"
        assert CommandCategory.CONFIG == "config"
        assert CommandCategory.QUERY == "query"


class TestCommandAction:
    def test_all_actions_exist(self):
        assert CommandAction.CLEAR_CONTEXT == "clear_context"
        assert CommandAction.COMPACT_CONTEXT == "compact_context"
        assert CommandAction.SHOW_HELP == "show_help"
        assert CommandAction.SHOW_STATUS == "show_status"
        assert CommandAction.SET_CONFIG == "set_config"
        assert CommandAction.LOAD_SKILL == "load_skill"
        assert CommandAction.NONE == "none"


class TestCommandResult:
    def test_defaults(self):
        r = CommandResult(action=CommandAction.NONE, message="hello")
        assert r.data == {}
        assert r.skill_content == ""

    def test_frozen(self):
        r = CommandResult(action=CommandAction.NONE, message="test")
        with pytest.raises(AttributeError):
            r.action = CommandAction.CLEAR_CONTEXT

    def test_load_skill_result(self):
        r = CommandResult(
            action=CommandAction.LOAD_SKILL,
            message="Loading skill",
            skill_content="skill body here",
        )
        assert r.skill_content == "skill body here"


class TestSlashCommand:
    def test_required_fields(self):
        cmd = SlashCommand(
            name="help",
            description="帮助",
            category=CommandCategory.QUERY,
        )
        assert cmd.category == CommandCategory.QUERY
        assert cmd.handler is None

    def test_handler_stored(self):
        def dummy(args: str) -> CommandResult:
            return CommandResult(action=CommandAction.NONE, message="ok")

        cmd = SlashCommand(
            name="help",
            description="帮助",
            category=CommandCategory.QUERY,
            handler=dummy,
        )
        assert cmd.handler is not None
