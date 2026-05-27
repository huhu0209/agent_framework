"""HookManager 测试。"""

import asyncio
from pathlib import Path

import pytest

from agent_framework.hooks.manager import HookManager, _parse_exit
from agent_framework.hooks.types import HookConfig, HookContext, HookEvent, HookType


# --- _parse_exit tests ---


def test_parse_exit_code_0_no_stdout():
    result = _parse_exit(0, "", "")
    assert result.exit_code == 0
    assert result.blocked is False
    assert result.updated_input is None


def test_parse_exit_code_0_with_valid_json():
    result = _parse_exit(
        0,
        '{"updatedInput": {"file_path": "/safe.py"}}',
        "",
    )
    assert result.exit_code == 0
    assert result.updated_input == {"file_path": "/safe.py"}


def test_parse_exit_code_0_with_invalid_json():
    result = _parse_exit(0, "not json at all", "")
    assert result.exit_code == 0
    assert result.updated_input is None


def test_parse_exit_code_0_json_without_updated_input():
    result = _parse_exit(0, '{"message": "ok"}', "")
    assert result.exit_code == 0
    assert result.updated_input is None


def test_parse_exit_code_1():
    result = _parse_exit(1, "", "permission denied")
    assert result.exit_code == 1
    assert result.blocked is True
    assert result.stderr == "permission denied"


def test_parse_exit_code_2():
    result = _parse_exit(2, "stdout msg", "inject this")
    assert result.exit_code == 2
    assert result.inject_message == "inject this"


def test_parse_exit_code_2_fallback_to_stdout():
    result = _parse_exit(2, "fallback msg", "")
    assert result.exit_code == 2
    assert result.inject_message == "fallback msg"


def test_parse_exit_code_other():
    result = _parse_exit(137, "", "killed")
    assert result.exit_code == 137
    assert result.blocked is True
    assert result.stderr == "killed"


# --- HookManager register/match/fire tests ---


@pytest.mark.asyncio
async def test_register_and_fire_untrusted():
    """未信任时 fire() 返回空列表。"""
    mgr = HookManager(trusted=False)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo ok",
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse"),
    )
    assert results == []


def test_match_star():
    mgr = HookManager()
    assert mgr._match("*", "Write") is True
    assert mgr._match("*", None) is True


def test_match_exact():
    mgr = HookManager()
    assert mgr._match("Write", "Write") is True
    assert mgr._match("Write", "Read") is False


def test_match_fnmatch():
    mgr = HookManager()
    assert mgr._match("mcp__*", "mcp__github__query") is True
    assert mgr._match("mcp__*", "echo") is False


def test_match_none_tool_name():
    mgr = HookManager()
    assert mgr._match("Write", None) is False


# --- _execute_command tests (trusted) ---


@pytest.mark.asyncio
async def test_fire_trusted_exit_0():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="exit 0",
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="echo"),
    )
    assert len(results) == 1
    assert results[0].exit_code == 0
    assert results[0].blocked is False


@pytest.mark.asyncio
async def test_fire_trusted_exit_0_with_updated_input():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command='echo \'{"updatedInput": {"msg": "safe"}}\'',
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="echo"),
    )
    assert len(results) == 1
    assert results[0].updated_input == {"msg": "safe"}


@pytest.mark.asyncio
async def test_fire_trusted_exit_1_blocks():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'denied' >&2; exit 1",
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="Write"),
    )
    assert len(results) == 1
    assert results[0].blocked is True
    assert "denied" in results[0].stderr


@pytest.mark.asyncio
async def test_fire_trusted_exit_2_injects():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.POST_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'extra info' >&2; exit 2",
    ))
    results = await mgr.fire(
        HookEvent.POST_TOOL_USE,
        HookContext(hook_event_name="PostToolUse", tool_name="Read"),
    )
    assert len(results) == 1
    assert results[0].exit_code == 2
    assert "extra info" in results[0].inject_message


@pytest.mark.asyncio
async def test_fire_receives_stdin_json():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command='python3 -c "import sys,json; d=json.load(sys.stdin); print(d[\'tool_name\'])"',
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(
            hook_event_name="PreToolUse",
            tool_name="Write",
            tool_input={"file": "x.py"},
        ),
    )
    assert len(results) == 1
    assert results[0].stdout == "Write"


@pytest.mark.asyncio
async def test_fire_timeout_returns_blocked():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="sleep 10",
        timeout=1,
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="echo"),
    )
    assert len(results) == 1
    assert results[0].blocked is True


@pytest.mark.asyncio
async def test_fire_session_id_auto_filled():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command='python3 -c "import sys,json; d=json.load(sys.stdin); print(d[\'session_id\'])"',
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="echo"),
    )
    assert len(results) == 1
    assert results[0].stdout == mgr._session_id


# --- load_from_json + once + matcher tests ---


def test_load_from_json(tmp_path):
    hooks_json = tmp_path / "hooks.json"
    hooks_json.write_text("""{
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {"type": "command", "command": "echo check", "timeout": 15}
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": "echo done", "once": true}
                    ]
                }
            ]
        }
    }""")

    mgr = HookManager(trusted=True)
    mgr.load_from_json(hooks_json)
    pre = mgr._hooks[HookEvent.PRE_TOOL_USE]
    post = mgr._hooks[HookEvent.POST_TOOL_USE]
    assert len(pre) == 1
    assert pre[0].matcher == "Write"
    assert pre[0].timeout == 15
    assert len(post) == 1
    assert post[0].once is True


def test_load_from_json_missing_file():
    mgr = HookManager()
    mgr.load_from_json(Path("/nonexistent/hooks.json"))
    assert len(mgr._hooks) == 0


@pytest.mark.asyncio
async def test_once_removes_after_fire():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.SESSION_START,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo start",
        once=True,
    ))
    results1 = await mgr.fire(
        HookEvent.SESSION_START,
        HookContext(hook_event_name="SessionStart"),
    )
    assert len(results1) == 1

    results2 = await mgr.fire(
        HookEvent.SESSION_START,
        HookContext(hook_event_name="SessionStart"),
    )
    assert len(results2) == 0


@pytest.mark.asyncio
async def test_matcher_filters_tool_name():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="Write",
        hook_type=HookType.COMMAND,
        command="echo blocked",
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="Read"),
    )
    assert len(results) == 0

    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="Write"),
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_multiple_hooks_fire_in_order():
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo first",
    ))
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo second",
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse", tool_name="echo"),
    )
    assert len(results) == 2
    assert results[0].stdout == "first"
    assert results[1].stdout == "second"


@pytest.mark.asyncio
async def test_fire_subprocess_error_returns_blocked(monkeypatch):
    """子进程启动失败时返回 blocked 而非抛异常。"""
    async def _fail(*args, **kwargs):
        raise OSError("bash not found")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fail)
    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="anything",
    ))
    results = await mgr.fire(
        HookEvent.PRE_TOOL_USE,
        HookContext(hook_event_name="PreToolUse"),
    )
    assert len(results) == 1
    assert results[0].blocked is True
    assert "bash not found" in results[0].stderr


# --- load_from_json 错误处理测试 ---


def test_load_from_json_malformed_json(tmp_path):
    """格式错误的 JSON 不崩溃，跳过加载。"""
    hooks_json = tmp_path / "hooks.json"
    hooks_json.write_text("{invalid json!!!")

    mgr = HookManager(trusted=True)
    mgr.load_from_json(hooks_json)
    assert len(mgr._hooks) == 0


def test_load_from_json_invalid_event_name(tmp_path):
    """无效的事件名不崩溃，跳过该条目。"""
    hooks_json = tmp_path / "hooks.json"
    hooks_json.write_text("""{
        "hooks": {
            "InvalidEvent": [
                {"matcher": "*", "hooks": [{"command": "echo ok"}]}
            ],
            "PreToolUse": [
                {"matcher": "*", "hooks": [{"command": "echo valid"}]}
            ]
        }
    }""")

    mgr = HookManager(trusted=True)
    mgr.load_from_json(hooks_json)
    assert len(mgr._hooks[HookEvent.PRE_TOOL_USE]) == 1
    assert len(mgr._hooks[HookEvent.SESSION_START]) == 0


def test_load_from_json_empty_command_skipped(tmp_path):
    """空 command 字符串被跳过。"""
    hooks_json = tmp_path / "hooks.json"
    hooks_json.write_text("""{
        "hooks": {
            "PreToolUse": [
                {"matcher": "*", "hooks": [
                    {"command": ""},
                    {"command": "  "},
                    {"command": "echo valid"}
                ]}
            ]
        }
    }""")

    mgr = HookManager(trusted=True)
    mgr.load_from_json(hooks_json)
    assert len(mgr._hooks[HookEvent.PRE_TOOL_USE]) == 1
    assert mgr._hooks[HookEvent.PRE_TOOL_USE][0].command == "echo valid"


def test_load_from_json_non_list_entries_skipped(tmp_path):
    """非列表类型的 entries 被跳过。"""
    hooks_json = tmp_path / "hooks.json"
    hooks_json.write_text("""{
        "hooks": {
            "PreToolUse": "not a list"
        }
    }""")

    mgr = HookManager(trusted=True)
    mgr.load_from_json(hooks_json)
    assert len(mgr._hooks) == 0
