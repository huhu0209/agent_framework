"""McpManager 测试 — 生命周期 + 工具注册 + 调用路由。"""

import sys
import pytest
from pydantic import ValidationError

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


class TestMcpEnvBlacklist:
    """McpServerConfig 敏感环境变量黑名单测试。"""

    def test_rejects_api_key(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"OPENAI_API_KEY": "sk-xxx"})

    def test_rejects_token(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"GITHUB_TOKEN": "ghp_xxx"})

    def test_rejects_secret_case_insensitive(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"My_Secret_Key": "xxx"})

    def test_rejects_password(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"DATABASE_PASSWORD": "xxx"})

    def test_rejects_credential(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"MY_CREDENTIAL_FILE": "xxx"})

    def test_rejects_access_key(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"AWS_ACCESS_KEY_ID": "xxx"})

    def test_rejects_private_key(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"SSH_PRIVATE_KEY": "xxx"})

    def test_allows_normal_env(self):
        cfg = McpServerConfig(name="test", command="echo", env={"PATH": "/usr/bin", "HOME": "/root"})
        assert cfg.env["PATH"] == "/usr/bin"
        assert cfg.env["HOME"] == "/root"

    def test_allows_debug_env(self):
        cfg = McpServerConfig(name="test", command="echo", env={"DEBUG": "true", "VERBOSE": "1"})
        assert cfg.env["DEBUG"] == "true"
        assert cfg.env["VERBOSE"] == "1"

    # --- 扩展模式测试 (Phase 16) ---

    def test_rejects_auth(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"AUTH_HEADER": "xxx"})

    def test_rejects_session(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"SESSION_ID": "xxx"})

    def test_rejects_cookie(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"COOKIE_VALUE": "xxx"})

    def test_rejects_bearer(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"BEARER_TOKEN": "xxx"})

    def test_rejects_refresh(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"REFRESH_TOKEN": "xxx"})

    def test_rejects_jwt(self):
        with pytest.raises(ValidationError, match="敏感"):
            McpServerConfig(name="test", command="echo", env={"JWT_SECRET": "xxx"})


class TestMcpShutdownLogging:
    """McpManager.shutdown 应在 client 关闭失败时记录日志。"""

    @pytest.mark.asyncio
    async def test_shutdown_logs_on_close_failure(self, caplog):
        """当 client.close() 抛异常时，shutdown 应记 debug 日志而非静默 pass。"""
        import logging

        class FailingClient:
            async def close(self):
                raise RuntimeError("close failed")

        manager = McpManager([])
        manager._clients["broken"] = FailingClient()

        with caplog.at_level(logging.DEBUG, logger="agent_framework.tools.mcp.config"):
            await manager.shutdown()

        assert any("broken" in r.message and "关闭失败" in r.message for r in caplog.records)
