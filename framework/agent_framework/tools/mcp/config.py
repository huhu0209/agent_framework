"""MCP 配置模型 + 生命周期管理。"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from pydantic import BaseModel

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.mcp.client import McpClient, McpToolError
from agent_framework.tools.mcp.transport import McpTransport, StdioTransport
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolResult, ToolSpec

logger = logging.getLogger(__name__)


class McpServerConfig(BaseModel):
    """单个 MCP server 的配置。"""

    name: str
    transport: Literal["stdio"] = "stdio"
    command: str = ""
    args: list[str] = []
    env: dict[str, str] = {}
    timeout_ms: int = 30_000

    url: str = ""
    headers: dict[str, str] = {}


class McpManager:
    """持有所有 McpClient，负责生命周期 + 工具注册 + 调用路由。"""

    def __init__(self, configs: list[McpServerConfig]) -> None:
        self._configs = configs
        self._clients: dict[str, McpClient] = {}

    async def start(self, registry: ToolRegistry) -> None:
        """启动时全量连接，逐个注册。单个失败跳过。"""
        for cfg in self._configs:
            try:
                transport = self._create_transport(cfg)
                client = McpClient(cfg.name, transport)
                await client.connect()
                self._register_tools(client, cfg, registry)
                self._clients[cfg.name] = client
            except Exception as e:
                logger.warning(f"MCP server '{cfg.name}' 启动失败，跳过: {e}")

    async def call_tool(
        self, server_name: str, tool_name: str, args: dict,
    ) -> ToolResult:
        """供 _dispatch_mcp 调用。"""
        client = self._clients.get(server_name)
        if client is None:
            return ToolResult(
                content=f"MCP server '{server_name}' 未连接",
                is_error=True,
            )
        try:
            result = await client.call_tool(tool_name, args)
            return self._to_tool_result(result)
        except McpToolError as e:
            return ToolResult(content=str(e), is_error=True)
        except (ConnectionError, asyncio.TimeoutError) as e:
            return ToolResult(
                content=f"MCP 工具不可用: {e}",
                is_error=True,
            )

    async def shutdown(self) -> None:
        """关闭所有 client。"""
        for client in self._clients.values():
            try:
                await client.close()
            except Exception:
                pass
        self._clients.clear()

    def _create_transport(self, cfg: McpServerConfig) -> McpTransport:
        if cfg.transport == "stdio":
            return StdioTransport(cfg.command, cfg.args, cfg.env or None)
        raise ValueError(f"不支持的传输类型: {cfg.transport}")

    def _register_tools(
        self, client: McpClient, cfg: McpServerConfig, registry: ToolRegistry,
    ) -> None:
        for tool_def in client.tools:
            prefixed_name = f"mcp__{cfg.name}__{tool_def['name']}"
            spec = ToolSpec(
                name=prefixed_name,
                description=tool_def.get("description", ""),
                parameters=tool_def.get(
                    "inputSchema",
                    ToolParameterSchema(),
                ),
                timeout_ms=cfg.timeout_ms,
                annotations=tool_def.get("annotations", {}),
            )
            registry.register(spec)

    @staticmethod
    def _to_tool_result(mcp_result: dict) -> ToolResult:
        is_error = mcp_result.get("isError", False)
        parts = []
        for block in mcp_result.get("content", []):
            if block.get("type") == "text":
                parts.append(block["text"])
        return ToolResult(content="\n".join(parts), is_error=is_error)
