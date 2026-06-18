"""McpManager 测试 — 生命周期 + 工具注册 + 调用路由。"""

import json
import logging
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from pydantic import ValidationError

from agent_framework.config.loader import ConfigLoader
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


def _make_loader_with_mcp_dirs(tmp_path: Path, dirs_and_servers: dict[str, dict | None]) -> ConfigLoader:
    """Create a ConfigLoader whose discover("mcp") returns the given directories.

    Args:
        tmp_path: Base temp directory.
        dirs_and_servers: Mapping of subdir name -> servers.json content (or None to skip).
    """
    mcp_dirs: list[Path] = []
    for subdir, content in dirs_and_servers.items():
        mcp_dir = tmp_path / subdir
        mcp_dir.mkdir(parents=True, exist_ok=True)
        if content is not None:
            (mcp_dir / "servers.json").write_text(json.dumps(content), encoding="utf-8")
        mcp_dirs.append(mcp_dir)

    loader = MagicMock(spec=ConfigLoader)
    loader.discover.return_value = mcp_dirs
    return loader


class TestMcpManagerFromLoader:
    """McpManager.from_loader() factory method tests."""

    def test_from_loader_no_mcp_dirs_returns_empty(self, tmp_path):
        """from_loader() with no mcp dirs returns McpManager with empty configs."""
        loader = _make_loader_with_mcp_dirs(tmp_path, {})
        manager = McpManager.from_loader(loader)
        assert manager._configs == []

    def test_from_loader_global_only_servers(self, tmp_path):
        """from_loader() with global-only servers.json loads all servers."""
        servers_json = {
            "servers": [
                {"name": "postgres", "command": "pg-mcp", "args": ["--port", "5432"]},
                {"name": "redis", "command": "redis-mcp"},
            ]
        }
        loader = _make_loader_with_mcp_dirs(tmp_path, {"global_mcp": servers_json})
        manager = McpManager.from_loader(loader)
        names = [c.name for c in manager._configs]
        assert "postgres" in names
        assert "redis" in names
        assert len(manager._configs) == 2

    def test_from_loader_global_plus_project_disjoint(self, tmp_path):
        """from_loader() with global+project servers.json, disjoint names, returns union."""
        global_json = {"servers": [{"name": "postgres", "command": "pg-mcp"}]}
        project_json = {"servers": [{"name": "redis", "command": "redis-mcp"}]}
        loader = _make_loader_with_mcp_dirs(tmp_path, {
            "global_mcp": global_json,
            "project_mcp": project_json,
        })
        manager = McpManager.from_loader(loader)
        names = [c.name for c in manager._configs]
        assert "postgres" in names
        assert "redis" in names
        assert len(manager._configs) == 2

    def test_from_loader_project_overrides_global_with_warning(self, tmp_path, caplog):
        """from_loader() with same server name in global+project, project overrides global."""
        global_json = {"servers": [{"name": "postgres", "command": "global-pg"}]}
        project_json = {"servers": [{"name": "postgres", "command": "project-pg"}]}
        loader = _make_loader_with_mcp_dirs(tmp_path, {
            "global_mcp": global_json,
            "project_mcp": project_json,
        })
        with caplog.at_level(logging.WARNING, logger="agent_framework.tools.mcp.config"):
            manager = McpManager.from_loader(loader)

        assert len(manager._configs) == 1
        assert manager._configs[0].command == "project-pg"
        assert any("postgres" in r.message for r in caplog.records)

    def test_from_loader_skips_dirs_without_servers_json(self, tmp_path):
        """from_loader() skips directories with no servers.json (no error)."""
        servers_json = {"servers": [{"name": "redis", "command": "redis-mcp"}]}
        loader = _make_loader_with_mcp_dirs(tmp_path, {
            "global_mcp": None,  # no servers.json
            "project_mcp": servers_json,
        })
        manager = McpManager.from_loader(loader)
        assert len(manager._configs) == 1
        assert manager._configs[0].name == "redis"

    def test_from_loader_skips_invalid_entries_with_warning(self, tmp_path, caplog):
        """from_loader() skips invalid JSON entries with warning, loads valid ones."""
        servers_json = {
            "servers": [
                {"name": "valid", "command": "echo"},
                {"bad": "entry"},  # missing required "name" field
            ]
        }
        loader = _make_loader_with_mcp_dirs(tmp_path, {"global_mcp": servers_json})
        with caplog.at_level(logging.WARNING, logger="agent_framework.tools.mcp.config"):
            manager = McpManager.from_loader(loader)

        assert len(manager._configs) == 1
        assert manager._configs[0].name == "valid"
        assert any("跳过" in r.message or "skip" in r.message.lower() for r in caplog.records)


def test_mcp_server_config_has_no_ghost_fields():
    """H-C3: url/headers 幽灵字段已删除（transport 锁死 stdio，零消费者）。"""
    fields = set(McpServerConfig.model_fields.keys())
    assert "url" not in fields
    assert "headers" not in fields


def test_register_tools_sets_non_strict_unknown_params():
    """H-C2: MCP 注册的 spec strict_unknown_params=False（远程 schema 不可信，不拒未知参数）。"""
    client = MagicMock()
    client.tools = [{"name": "query", "description": "SQL", "inputSchema": {"type": "object", "properties": {}}}]
    cfg = McpServerConfig(name="db", command="cmd")
    registry = ToolRegistry()
    manager = McpManager([])
    manager._register_tools(client, cfg, registry)

    spec = registry.get("mcp__db__query")
    assert spec is not None
    assert spec.strict_unknown_params is False
