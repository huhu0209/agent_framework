"""MCP Client — JSON-RPC 2.0 协议语义 + MCP 握手。"""

from __future__ import annotations

import logging

from agent_framework.tools.mcp.transport import McpTransport

logger = logging.getLogger(__name__)


class McpToolError(Exception):
    """MCP tools/call 返回的协议层错误。"""


class McpClient:
    """单个 MCP server 的客户端。

    职责：JSON-RPC id 管理 + initialize 握手 + tools/list 发现 + tools/call 调用。
    不负责注册到 ToolRegistry（那是 McpManager 的事）。
    """

    def __init__(self, name: str, transport: McpTransport) -> None:
        self.name = name
        self._transport = transport
        self._next_id = 1
        self._tools: list[dict] = []

    @property
    def tools(self) -> list[dict]:
        return self._tools

    async def connect(self) -> None:
        """建立连接 + MCP 握手 + 工具发现。"""
        await self._transport.connect()

        await self._send_request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "agent-framework", "version": "0.1.0"},
        })

        await self._transport.send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })

        tools_result = await self._send_request("tools/list", {})
        self._tools = tools_result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用工具，返回 JSON-RPC result 或抛 McpToolError。"""
        return await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

    async def close(self) -> None:
        await self._transport.close()

    async def _send_request(self, method: str, params: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }
        self._next_id += 1
        response = await self._transport.send(payload)
        if "error" in response:
            raise McpToolError(response["error"]["message"])
        return response["result"]
