"""Tool System 模块。

提供工具注册、路由、执行能力。
"""

from .executor import ToolExecutor
from .mcp import McpClient, McpManager, McpServerConfig, McpToolError, McpTransport, StdioTransport
from .registry import ToolRegistry
from .router import ToolRouter
from .types import ToolCall, ToolHandler, ToolResult, ToolSpec, ToolUseContext
from .validator import ToolValidator

__all__ = [
    "McpClient",
    "McpManager",
    "McpServerConfig",
    "McpToolError",
    "McpTransport",
    "StdioTransport",
    "ToolCall",
    "ToolHandler",
    "ToolResult",
    "ToolSpec",
    "ToolUseContext",
    "ToolRegistry",
    "ToolRouter",
    "ToolExecutor",
    "ToolValidator",
]
