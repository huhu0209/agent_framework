"""McpClient 测试 — JSON-RPC 2.0 + 握手。"""

import json
import sys
import pytest
from agent_framework.tools.mcp.client import McpClient, McpToolError
from agent_framework.tools.mcp.transport import StdioTransport


# 支持 MCP 握手协议的假 server
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
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-server", "version": "1.0.0"},
            },
        })
    elif method == "tools/list":
        write_message({
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "tools": [
                    {
                        "name": "query",
                        "description": "Execute SQL",
                        "inputSchema": {"type": "object", "properties": {"sql": {"type": "string"}}},
                    },
                    {
                        "name": "list_tables",
                        "description": "List all tables",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ],
            },
        })
    elif method == "tools/call":
        tool_name = msg["params"]["name"]
        if tool_name == "fail_tool":
            write_message({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "error": {"code": -32600, "message": "Tool execution failed"},
            })
        else:
            write_message({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "content": [{"type": "text", "text": f"result of {tool_name}"}],
                    "isError": False,
                },
            })
'''


@pytest.fixture
def mcp_server_script(tmp_path):
    script = tmp_path / "mcp_server.py"
    script.write_text(MCP_SERVER_SCRIPT)
    return str(script)


@pytest.fixture
async def connected_client(mcp_server_script):
    transport = StdioTransport(
        command=sys.executable,
        args=[mcp_server_script],
    )
    client = McpClient(name="test_server", transport=transport)
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_connect_discovers_tools(connected_client):
    assert len(connected_client.tools) == 2
    assert connected_client.tools[0]["name"] == "query"
    assert connected_client.tools[1]["name"] == "list_tables"


@pytest.mark.asyncio
async def test_call_tool_returns_result(connected_client):
    result = await connected_client.call_tool("query", {"sql": "SELECT 1"})
    assert result["content"][0]["text"] == "result of query"
    assert result["isError"] is False


@pytest.mark.asyncio
async def test_call_tool_error_raises(connected_client):
    with pytest.raises(McpToolError, match="Tool execution failed"):
        await connected_client.call_tool("fail_tool", {})


@pytest.mark.asyncio
async def test_id_increments(connected_client):
    assert connected_client._next_id > 1
