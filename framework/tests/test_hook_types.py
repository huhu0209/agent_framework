"""Hook 类型定义测试。"""

from dataclasses import FrozenInstanceError

import pytest

from agent_framework.hooks.types import (
    HookConfig,
    HookContext,
    HookEvent,
    HookResult,
    HookType,
)


def test_hook_type_enum():
    assert HookType.COMMAND == "command"


def test_hook_event_enum():
    assert HookEvent.SESSION_START == "SessionStart"
    assert HookEvent.PRE_TOOL_USE == "PreToolUse"
    assert HookEvent.POST_TOOL_USE == "PostToolUse"


def test_hook_config_defaults():
    config = HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="Write",
        hook_type=HookType.COMMAND,
        command="echo ok",
    )
    assert config.timeout == 30
    assert config.once is False


def test_hook_config_frozen():
    config = HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo ok",
    )
    with pytest.raises(FrozenInstanceError):
        config.command = "new command"


def test_hook_context_defaults():
    ctx = HookContext(hook_event_name="PreToolUse")
    assert ctx.session_id == ""
    assert ctx.tool_name is None
    assert ctx.tool_input is None
    assert ctx.tool_result is None


def test_hook_context_frozen():
    ctx = HookContext(hook_event_name="PreToolUse")
    with pytest.raises(FrozenInstanceError):
        ctx.session_id = "new"


def test_hook_result_exit_code_0():
    result = HookResult(exit_code=0)
    assert result.blocked is False
    assert result.inject_message == ""
    assert result.updated_input is None


def test_hook_result_exit_code_1():
    result = HookResult(exit_code=1, blocked=True, stderr="denied")
    assert result.blocked is True
    assert result.stderr == "denied"


def test_hook_result_frozen():
    result = HookResult(exit_code=0)
    with pytest.raises(FrozenInstanceError):
        result.exit_code = 1
