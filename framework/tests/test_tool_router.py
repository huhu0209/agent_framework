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
