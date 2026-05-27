"""ToolRouter 测试 — 来源分叉。"""

import sys
import pytest
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolCall, ToolResult, ToolSpec, ToolUseContext
from agent_framework.llm.types import ToolParameterSchema


async def _echo_handler(args, ctx):
    return ToolResult(content=f"echo: {args.get('msg', '')}")


def _make_registry_with_echo() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="echo",
        description="echo tool",
        parameters=ToolParameterSchema(
            properties={"msg": {"type": "string"}},
            required=["msg"],
        ),
        handler=_echo_handler,
    ))
    return registry


ctx = ToolUseContext()


@pytest.mark.asyncio
async def test_builtin_dispatch():
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_1", name="echo", arguments={"msg": "hello"}),
        ctx,
    )
    assert result.content == "echo: hello"
    assert result.is_error is False


@pytest.mark.asyncio
async def test_unknown_builtin_returns_error():
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_2", name="nonexistent", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未知工具" in result.content


@pytest.mark.asyncio
async def test_mcp_prefix_returns_not_configured():
    """未配置 McpManager 时 MCP 工具返回未配置错误。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_3", name="mcp__github__create_issue", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未配置" in result.content


@pytest.mark.asyncio
async def test_agent_prefix_returns_not_implemented():
    """Agent-as-tool 路由已预留，返回未实现。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_4", name="agent__coder", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未实现" in result.content


# --- MCP 集成测试 ---

MCP_ECHO_SCRIPT = '''
import sys
import json

def read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    if line.startswith("Content-Length:"):
        length = int(line.split(":")[1].strip())
        sys.stdin.readline()
        body = sys.stdin.read(length)
        return json.loads(body)
    return None

def write_message(msg):
    body = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(body)}\\r\\n\\r\\n{body}")
    sys.stdout.flush()

while True:
    msg = read_message()
    if msg is None:
        break
    method = msg.get("method", "")
    if method == "initialize":
        write_message({
            "jsonrpc": "2.0", "id": msg["id"],
            "result": {"protocolVersion": "2025-03-26", "capabilities": {}, "serverInfo": {"name": "fake", "version": "1.0"}},
        })
    elif method == "tools/list":
        write_message({
            "jsonrpc": "2.0", "id": msg["id"],
            "result": {"tools": [{"name": "query", "description": "SQL", "inputSchema": {"type": "object", "properties": {}}}]},
        })
    elif method == "tools/call":
        write_message({
            "jsonrpc": "2.0", "id": msg["id"],
            "result": {"content": [{"type": "text", "text": "query ok"}], "isError": False},
        })
'''


@pytest.mark.asyncio
async def test_mcp_dispatch_with_manager(tmp_path):
    """MCP 工具通过 McpManager 路由到真实子进程。"""
    from agent_framework.tools.mcp.config import McpManager, McpServerConfig

    script = tmp_path / "echo.py"
    script.write_text(MCP_ECHO_SCRIPT)

    config = McpServerConfig(name="db", command=sys.executable, args=[str(script)])
    manager = McpManager([config])
    registry = _make_registry_with_echo()
    await manager.start(registry)

    router = ToolRouter(registry, mcp_manager=manager)
    result = await router.dispatch(
        ToolCall(id="tc_m1", name="mcp__db__query", arguments={}),
        ctx,
    )
    assert result.is_error is False
    assert result.content == "query ok"

    await manager.shutdown()


@pytest.mark.asyncio
async def test_mcp_dispatch_no_manager():
    """未配置 McpManager 时 MCP 工具返回错误。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_m2", name="mcp__db__query", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未配置" in result.content


@pytest.mark.asyncio
async def test_mcp_dispatch_invalid_name():
    """无效的 MCP 工具名返回错误。"""
    from agent_framework.tools.mcp.config import McpManager

    registry = ToolRegistry()
    router = ToolRouter(registry, mcp_manager=McpManager([]))
    result = await router.dispatch(
        ToolCall(id="tc_m3", name="mcp__invalid", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "无效" in result.content


# --- 权限管道集成测试 ---


@pytest.mark.asyncio
async def test_dispatch_denied_tool():
    """权限管道拒绝的工具返回错误。"""
    from agent_framework.prompts.profiles import AgentProfile
    from agent_framework.safety.permissions import PermissionPipeline

    profile = AgentProfile(
        name="reader",
        description="readonly",
        soul="", agents_rules="", identity="",
        disallowed_tools=["write_file"],
    )
    pipeline = PermissionPipeline(profile=profile)
    registry = _make_registry_with_echo()
    router = ToolRouter(registry=registry)
    router.set_permission_pipeline(pipeline)

    call = ToolCall(id="1", name="write_file", arguments={"path": "a.txt"})
    result = await router.dispatch(call, ToolUseContext(working_dir="."))
    assert result.is_error
    assert "拒绝" in result.content


@pytest.mark.asyncio
async def test_dispatch_allowed_tool_passes():
    """权限管道允许的工具正常执行。"""
    from agent_framework.prompts.profiles import AgentProfile
    from agent_framework.safety.permissions import PermissionPipeline

    profile = AgentProfile(
        name="reader",
        description="readonly",
        soul="", agents_rules="", identity="",
        allowed_tools=["echo"],
    )
    pipeline = PermissionPipeline(profile=profile)
    registry = _make_registry_with_echo()
    router = ToolRouter(registry=registry)
    router.set_permission_pipeline(pipeline)

    call = ToolCall(id="1", name="echo", arguments={"msg": "hi"})
    result = await router.dispatch(call, ToolUseContext(working_dir="."))
    assert not result.is_error
    assert "echo: hi" in result.content


@pytest.mark.asyncio
async def test_dispatch_no_pipeline_passes_all():
    """无权限管道时所有工具直接通过。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry=registry)

    call = ToolCall(id="1", name="echo", arguments={"msg": "free"})
    result = await router.dispatch(call, ToolUseContext(working_dir="."))
    assert not result.is_error


# --- Hooks 集成测试 ---


@pytest.mark.asyncio
async def test_dispatch_with_pre_tool_hook_blocked():
    """PreToolUse hook 阻止工具执行。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'blocked by policy' >&2; exit 1",
    ))
    registry = _make_registry_with_echo()
    router = ToolRouter(registry, hook_manager=mgr)
    result = await router.dispatch(
        ToolCall(id="h1", name="echo", arguments={"msg": "hi"}),
        ctx,
    )
    assert result.is_error is True
    assert "Hook blocked" in result.content


@pytest.mark.asyncio
async def test_dispatch_with_pre_tool_hook_modify_input():
    """PreToolUse hook 修改工具参数。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command='echo \'{"updatedInput": {"msg": "modified"}}\'',
    ))
    registry = _make_registry_with_echo()
    router = ToolRouter(registry, hook_manager=mgr)
    result = await router.dispatch(
        ToolCall(id="h2", name="echo", arguments={"msg": "original"}),
        ctx,
    )
    assert result.is_error is False
    assert result.content == "echo: modified"


@pytest.mark.asyncio
async def test_dispatch_with_post_tool_hook_inject():
    """PostToolUse hook 注入补充信息。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.POST_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'extra info' >&2; exit 2",
    ))
    registry = _make_registry_with_echo()
    router = ToolRouter(registry, hook_manager=mgr)
    result = await router.dispatch(
        ToolCall(id="h3", name="echo", arguments={"msg": "hi"}),
        ctx,
    )
    assert result.is_error is False
    assert "echo: hi" in result.content
    assert "extra info" in result.content


@pytest.mark.asyncio
async def test_dispatch_with_no_hook_manager():
    """无 HookManager 时正常执行（向后兼容）。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="h4", name="echo", arguments={"msg": "clean"}),
        ctx,
    )
    assert result.content == "echo: clean"
    assert result.is_error is False


@pytest.mark.asyncio
async def test_dispatch_permission_then_hook_order():
    """Permission deny → Hook 不执行。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType
    from agent_framework.prompts.profiles import AgentProfile
    from agent_framework.safety.permissions import PermissionPipeline

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'should not run'",
    ))

    profile = AgentProfile(
        name="strict",
        description="no echo",
        soul="", agents_rules="", identity="",
        disallowed_tools=["echo"],
    )
    pipeline = PermissionPipeline(profile=profile)

    registry = _make_registry_with_echo()
    router = ToolRouter(registry, hook_manager=mgr)
    router.set_permission_pipeline(pipeline)

    result = await router.dispatch(
        ToolCall(id="h5", name="echo", arguments={"msg": "test"}),
        ctx,
    )
    assert result.is_error is True
    assert "拒绝" in result.content


@pytest.mark.asyncio
async def test_dispatch_multiple_pre_tool_hooks_first_blocks():
    """第一个 PreToolUse hook block 后，第二个 hook 的 updated_input 不生效。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'blocked' >&2; exit 1",
    ))
    mgr.register(HookConfig(
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command='echo \'{"updatedInput": {"msg": "should not apply"}}\'',
    ))

    registry = _make_registry_with_echo()
    router = ToolRouter(registry, hook_manager=mgr)
    result = await router.dispatch(
        ToolCall(id="h6", name="echo", arguments={"msg": "original"}),
        ctx,
    )
    assert result.is_error is True
    assert "Hook blocked" in result.content


@pytest.mark.asyncio
async def test_dispatch_post_tool_hook_blocked_ignored():
    """PostToolUse hook 返回 exit 1 (blocked) 被忽略——工具已执行无法撤回。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.POST_TOOL_USE,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'should block' >&2; exit 1",
    ))

    registry = _make_registry_with_echo()
    router = ToolRouter(registry, hook_manager=mgr)
    result = await router.dispatch(
        ToolCall(id="h7", name="echo", arguments={"msg": "ran"}),
        ctx,
    )
    # 工具结果正常返回，blocked 被忽略
    assert result.is_error is False
    assert result.content == "echo: ran"


# --- 错误恢复与降级测试 ---


async def _crash_handler(args, ctx):
    raise RuntimeError("工具内部崩溃")


async def _slow_handler(args, ctx):
    import asyncio
    await asyncio.sleep(10)
    return ToolResult(content="不应该到这里")


def _make_registry_with_crash() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="crash_tool",
        description="会崩溃的工具",
        parameters=ToolParameterSchema(properties={}, required=[]),
        handler=_crash_handler,
        timeout_ms=100,
    ))
    registry.register(ToolSpec(
        name="slow_tool",
        description="会超时的工具",
        parameters=ToolParameterSchema(properties={}, required=[]),
        handler=_slow_handler,
        timeout_ms=50,
    ))
    return registry


@pytest.mark.asyncio
async def test_dispatch_tool_crash_returns_error():
    """工具 handler 抛异常 → 返回 is_error=True，不崩溃。"""
    registry = _make_registry_with_crash()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="e1", name="crash_tool", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "崩溃" in result.content or "crash" in result.content.lower() or "失败" in result.content


@pytest.mark.asyncio
async def test_dispatch_tool_timeout_returns_error():
    """工具超时 → 返回 is_error=True。"""
    registry = _make_registry_with_crash()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="e2", name="slow_tool", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "超时" in result.content


@pytest.mark.asyncio
async def test_dispatch_with_degrader_fallback():
    """工具失败 + 有降级映射 → 自动使用降级工具。"""
    from agent_framework.tools.degrader import ToolDegrader

    registry = _make_registry_with_echo()
    registry.register(ToolSpec(
        name="crash_tool",
        description="会崩溃",
        parameters=ToolParameterSchema(properties={}, required=[]),
        handler=_crash_handler,
    ))

    degrader = ToolDegrader()
    degrader.register("crash_tool", "echo")

    router = ToolRouter(registry, degrader=degrader)
    result = await router.dispatch(
        ToolCall(id="e3", name="crash_tool", arguments={"msg": "fallback"}),
        ctx,
    )
    assert result.is_error is False
    assert "echo: fallback" in result.content


@pytest.mark.asyncio
async def test_dispatch_degrader_no_fallback_returns_error():
    """工具失败 + 无降级映射 → 返回错误。"""
    registry = _make_registry_with_crash()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="e4", name="crash_tool", arguments={}),
        ctx,
    )
    assert result.is_error is True
