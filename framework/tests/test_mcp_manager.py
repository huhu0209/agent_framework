"""McpManager 测试 — 生命周期 + 工具注册 + 调用路由。"""

import sys
import pytest
from agent_framework.tools.mcp.config import McpManager, McpServerConfig
from agent_framework.tools.registry import ToolRegistry


MCP_SERVER_SCRIPT = '''
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
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "1.0"},
            },
        })
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        write_message({
            "jsonrpc": "2.0", "id": msg["id"],
            "result": {
                "tools": [{
                    "name": "query",
                    "description": "Execute SQL",
                    "inputSchema": {"type": "object", "properties": {"sql": {"type": "string"}}},
                }],
            },
        })
    elif method == "tools/call":
        write_message({
            "jsonrpc": "2.0", "id": msg["id"],
            "result": {
                "content": [{"type": "text", "text": "query result"}],
                "isError": False,
            },
        })
'''


@pytest.fixture
def server_script(tmp_path):
    script = tmp_path / "mcp_server.py"
    script.write_text(MCP_SERVER_SCRIPT)
    return str(script)


@pytest.mark.asyncio
async def test_manager_start_registers_tools(server_script):
    config = McpServerConfig(
        name="postgres",
        command=sys.executable,
        args=[server_script],
    )
    manager = McpManager([config])
    registry = ToolRegistry()

    await manager.start(registry)

    assert "mcp__postgres__query" in registry.list_tools()
    spec = registry.get("mcp__postgres__query")
    assert spec is not None
    assert spec.description == "Execute SQL"
    assert spec.timeout_ms == 30_000
    assert spec.handler is None

    await manager.shutdown()


@pytest.mark.asyncio
async def test_manager_call_tool(server_script):
    config = McpServerConfig(name="postgres", command=sys.executable, args=[server_script])
    manager = McpManager([config])
    registry = ToolRegistry()
    await manager.start(registry)

    result = await manager.call_tool("postgres", "query", {"sql": "SELECT 1"})
    assert result.is_error is False
    assert result.content == "query result"

    await manager.shutdown()


@pytest.mark.asyncio
async def test_manager_call_unknown_server():
    manager = McpManager([])
    result = await manager.call_tool("unknown", "query", {})
    assert result.is_error is True
    assert "未连接" in result.content


@pytest.mark.asyncio
async def test_manager_start_failure_skips(tmp_path):
    crash_script = tmp_path / "crash.py"
    crash_script.write_text("import sys; sys.exit(1)")

    ok_script = tmp_path / "ok.py"
    ok_script.write_text(MCP_SERVER_SCRIPT)

    configs = [
        McpServerConfig(name="crash", command=sys.executable, args=[str(crash_script)]),
        McpServerConfig(name="ok", command=sys.executable, args=[str(ok_script)]),
    ]
    manager = McpManager(configs)
    registry = ToolRegistry()
    await manager.start(registry)

    assert "mcp__ok__query" in registry.list_tools()
    assert "mcp__crash__query" not in registry.list_tools()

    await manager.shutdown()


@pytest.mark.asyncio
async def test_manager_shutdown_closes_all(server_script):
    config = McpServerConfig(name="postgres", command=sys.executable, args=[server_script])
    manager = McpManager([config])
    registry = ToolRegistry()
    await manager.start(registry)
    assert len(manager._clients) == 1

    await manager.shutdown()
    assert len(manager._clients) == 0
