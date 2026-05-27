"""commands/types.py 类型定义测试。"""

import pytest

from agent_framework.commands.types import CommandSource, ResolvedCommand, SlashCommand


class TestCommandSource:
    def test_builtin_value(self):
        assert CommandSource.BUILTIN == "builtin"

    def test_skill_value(self):
        assert CommandSource.SKILL == "skill"


class TestResolvedCommand:
    def test_defaults(self):
        cmd = ResolvedCommand(is_command=False, content="hello")
        assert cmd.source is None
        assert cmd.skill_loaded is False

    def test_frozen(self):
        cmd = ResolvedCommand(is_command=True, content="test", source=CommandSource.BUILTIN)
        with pytest.raises(AttributeError):
            cmd.is_command = False


class TestSlashCommand:
    def test_optional_fields_default(self):
        cmd = SlashCommand(name="help", description="帮助", source=CommandSource.BUILTIN)
        assert cmd.arg_hint == ""
        assert cmd.handler is None

    def test_handler_stored(self):
        def dummy(args: str) -> ResolvedCommand:
            return ResolvedCommand(is_command=True, content="ok")

        cmd = SlashCommand(name="help", description="帮助", source=CommandSource.BUILTIN, handler=dummy)
        assert cmd.handler is not None
