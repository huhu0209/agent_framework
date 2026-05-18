"""McpTransport 测试 — ABC 契约 + StdioTransport 分帧。"""

import asyncio
import json
import sys
import pytest
from agent_framework.tools.mcp.transport import McpTransport, StdioTransport


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
