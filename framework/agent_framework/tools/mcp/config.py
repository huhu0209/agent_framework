"""MCP 配置模型 + 生命周期管理。"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

from agent_framework.config.loader import ConfigLoader
from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.mcp.client import McpClient, McpToolError
from agent_framework.tools.mcp.transport import McpTransport, StdioTransport
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolResult, ToolSpec

logger = logging.getLogger(__name__)

_BLOCKED_ENV_PATTERNS: tuple[str, ...] = (
    "api_key",
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
    "access_key",
    "auth",
    "session",
    "cookie",
    "bearer",
    "refresh",
    "jwt",
)


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

    @field_validator("env")
    @classmethod
    def _reject_sensitive_env_keys(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            lowered = key.lower()
            if any(pattern in lowered for pattern in _BLOCKED_ENV_PATTERNS):
                raise ValueError(
                    f"MCP 配置不允许覆盖敏感环境变量: '{key}'"
                )
        return v


class McpManager:
    """持有所有 McpClient，负责生命周期 + 工具注册 + 调用路由。"""

    def __init__(self, configs: list[McpServerConfig]) -> None:
        self._configs = configs
        self._clients: dict[str, McpClient] = {}

    @classmethod
    def from_loader(cls, loader: ConfigLoader) -> McpManager:
        """从 ConfigLoader.discover("mcp") 路径加载 server 配置。

        按 natural order（global → project）迭代，后写入覆盖先写入。
        项目级同名 server 覆盖全局配置，并记录 warning。
        无效条目跳过并记录 warning。
        """
        server_map: dict[str, McpServerConfig] = {}

        for mcp_dir in loader.discover("mcp"):
            servers_file = mcp_dir / "servers.json"
            if not servers_file.exists():
                continue

            try:
                raw = json.loads(servers_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("无法读取 %s: %s，跳过", servers_file, exc)
                continue

            entries = raw.get("servers", [])
            for entry in entries:
                try:
                    cfg = McpServerConfig.model_validate(entry)
                except Exception as exc:
                    name = entry.get("name", "<unknown>")
                    logger.warning("MCP server '%s' 配置无效: %s，跳过", name, exc)
                    continue

                if cfg.name in server_map:
                    logger.warning(
                        "MCP server '%s' 重复定义，使用项目级覆盖全局", cfg.name,
                    )
                server_map[cfg.name] = cfg

        return cls(configs=list(server_map.values()))

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
        for name, client in self._clients.items():
            try:
                await client.close()
            except Exception:
                logger.debug("MCP client '%s' 关闭失败", name)
        self._clients.clear()

    def _create_transport(self, cfg: McpServerConfig) -> McpTransport:
        if cfg.transport == "stdio":
            return StdioTransport(cfg.command, cfg.args, cfg.env or None)
        raise ValueError(f"不支持的传输类型: {cfg.transport}")

    def _register_tools(
        self, client: McpClient, cfg: McpServerConfig, registry: ToolRegistry,
    ) -> None:
        """注册 MCP 工具到 ToolRegistry。

        MCP ToolSpec 对象是 schema-only 定义（无 handler 函数）。
        handler 为 None 是有意设计：执行通过 ToolRouter.dispatch() 中
        的 "mcp__" 前缀约定路由到 McpManager._dispatch_mcp()。
        直接通过 ToolExecutor 执行 MCP ToolSpec 会失败——
        它们必须经过 ToolRouter 的 mcp__ 前缀路由。
        """
        for tool_def in client.tools:
            prefixed_name = f"mcp__{cfg.name}__{tool_def['name']}"
            # handler=None is intentional: schema-only ToolSpec, routed via mcp__ prefix
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
