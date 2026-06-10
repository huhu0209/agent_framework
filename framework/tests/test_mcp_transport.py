"""McpTransport 测试 — ABC 契约 + StdioTransport 分帧。"""

import asyncio
import json
import os
import sys
import pytest
from agent_framework.tools.mcp.transport import McpTransport, StdioTransport, _ALLOWED_ENV_KEYS


def _make_transport_with_reader(data: bytes) -> StdioTransport:
    """创建一个 StdioTransport 实例，其 _process.stdout 被替换为含指定数据的 StreamReader。"""
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    transport = StdioTransport(command="true")
    transport._process = type("FakeProc", (), {"stdout": reader})()
    return transport


# --- ABC 测试 ---

def test_mcp_transport_is_abstract():
    with pytest.raises(TypeError):
        McpTransport()


def test_mcp_transport_required_methods():
    methods = {"connect", "close", "send", "send_notification"}
    assert methods.issubset(dir(McpTransport))


# --- StdioTransport 测试 ---

FAKE_SERVER_SCRIPT = '''
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
    if "id" in msg:
        write_message({
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {"echo": msg.get("method", "unknown")},
        })
'''


@pytest.fixture
def fake_server_script(tmp_path):
    script = tmp_path / "fake_mcp_server.py"
    script.write_text(FAKE_SERVER_SCRIPT)
    return str(script)


@pytest.mark.asyncio
async def test_stdio_connect_and_send(fake_server_script):
    transport = StdioTransport(
        command=sys.executable,
        args=[fake_server_script],
    )
    await transport.connect()
    try:
        response = await transport.send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })
        assert response["id"] == 1
        assert response["result"]["echo"] == "test"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_stdio_serial_sends(fake_server_script):
    transport = StdioTransport(
        command=sys.executable,
        args=[fake_server_script],
    )
    await transport.connect()
    try:
        r1 = await transport.send({"jsonrpc": "2.0", "id": 1, "method": "first"})
        r2 = await transport.send({"jsonrpc": "2.0", "id": 2, "method": "second"})
        assert r1["result"]["echo"] == "first"
        assert r2["result"]["echo"] == "second"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_stdio_send_notification(fake_server_script):
    transport = StdioTransport(
        command=sys.executable,
        args=[fake_server_script],
    )
    await transport.connect()
    try:
        await transport.send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        r = await transport.send({"jsonrpc": "2.0", "id": 1, "method": "after_notify"})
        assert r["result"]["echo"] == "after_notify"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_stdio_server_crash(tmp_path):
    crash_script = tmp_path / "crash_server.py"
    crash_script.write_text("import sys; sys.exit(1)")
    transport = StdioTransport(
        command=sys.executable,
        args=[str(crash_script)],
    )
    await transport.connect()
    with pytest.raises(ConnectionError):
        await asyncio.wait_for(
            transport.send({"jsonrpc": "2.0", "id": 1, "method": "test"}),
            timeout=5,
        )
    await transport.close()


@pytest.mark.asyncio
async def test_stdio_close_cleanup(fake_server_script):
    transport = StdioTransport(
        command=sys.executable,
        args=[fake_server_script],
    )
    await transport.connect()
    process = transport._process
    await transport.close()
    assert process.returncode is not None


# --- readline header 解析测试 ---


@pytest.mark.asyncio
async def test_read_until_header_end_single_header():
    """单行 header：Content-Length 后立即结束。"""
    transport = _make_transport_with_reader(b"Content-Length: 10\r\n\r\n")
    result = await transport._read_until_header_end()
    assert result == b"Content-Length: 10\r\n\r\n"


@pytest.mark.asyncio
async def test_read_until_header_end_multi_header():
    """多行 header：Content-Length + Custom 后结束。"""
    transport = _make_transport_with_reader(
        b"Content-Length: 10\r\nCustom: value\r\n\r\n"
    )
    result = await transport._read_until_header_end()
    assert b"Content-Length: 10" in result
    assert b"Custom: value" in result
    assert result.endswith(b"\r\n\r\n")


@pytest.mark.asyncio
async def test_read_until_header_end_eof():
    """连接关闭（空数据）应抛出 EOFError。"""
    transport = _make_transport_with_reader(b"")
    with pytest.raises(EOFError):
        await transport._read_until_header_end()


# --- 白名单 env 测试 ---


def test_allowed_env_keys_is_frozenset():
    """_ALLOWED_ENV_KEYS 应为 frozenset。"""
    assert isinstance(_ALLOWED_ENV_KEYS, frozenset)


def test_allowed_env_keys_includes_essentials():
    """白名单应包含基础环境变量。"""
    expected = {"PATH", "HOME", "TEMP", "TMP", "TMPDIR", "USER", "LANG", "SYSTEMROOT"}
    assert expected.issubset(_ALLOWED_ENV_KEYS)


@pytest.mark.asyncio
async def test_connect_env_uses_whitelist_not_full_environ(monkeypatch, tmp_path):
    """子进程只继承白名单环境变量，不继承全部 os.environ。"""
    monkeypatch.setenv("MY_SECRET_API_KEY", "should-not-leak")
    monkeypatch.setenv("MY_DANGEROUS_TOKEN", "should-not-leak")

    # 用一个脚本把环境变量写入临时文件
    outfile = tmp_path / "child_env.json"
    dump_script = tmp_path / "dump_env.py"
    dump_script.write_text(
        f"import os, json\n"
        f"env = dict(os.environ)\n"
        f"with open({str(outfile)!r}, 'w') as f:\n"
        f"    json.dump(env, f)\n"
    )

    transport = StdioTransport(
        command=sys.executable,
        args=[str(dump_script)],
    )
    await transport.connect()
    await transport._process.wait()

    with open(outfile) as f:
        child_env = json.load(f)

    # 敏感变量不应泄漏到子进程
    assert "MY_SECRET_API_KEY" not in child_env
    assert "MY_DANGEROUS_TOKEN" not in child_env

    await transport.close()


@pytest.mark.asyncio
async def test_connect_env_merges_config_env_on_top(monkeypatch, tmp_path):
    """config env 应合并在白名单基座之上。"""
    # 确保白名单中有 HOME
    if "HOME" not in os.environ:
        monkeypatch.setenv("HOME", "/original")

    outfile = tmp_path / "child_env2.json"
    dump_script = tmp_path / "dump_env2.py"
    dump_script.write_text(
        f"import os, json\n"
        f"env = dict(os.environ)\n"
        f"with open({str(outfile)!r}, 'w') as f:\n"
        f"    json.dump(env, f)\n"
    )

    transport = StdioTransport(
        command=sys.executable,
        args=[str(dump_script)],
        env={"MY_CUSTOM_VAR": "hello"},
    )
    await transport.connect()
    await transport._process.wait()

    with open(outfile) as f:
        child_env = json.load(f)

    # config env 应出现在子进程中
    assert child_env.get("MY_CUSTOM_VAR") == "hello"

    await transport.close()
