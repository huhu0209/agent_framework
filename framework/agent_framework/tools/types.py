"""Tool System 核心类型定义。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field

from agent_framework.llm.types import ToolDefinition, ToolParameterSchema


class ToolCall(BaseModel):
    """从 LLM 返回的 ToolUseBlock 提取的调用请求。"""

    id: str
    name: str
    arguments: dict[str, Any] = {}


class ToolResult(BaseModel):
    """结构化的工具执行结果。"""

    content: str
    is_error: bool = False
    metadata: dict[str, Any] = {}


class ToolSpec(BaseModel):
    """工具完整描述：LLM schema + handler 引用。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    parameters: ToolParameterSchema
    timeout_ms: int = 30_000
    handler: Any = Field(exclude=True, repr=False)

    def to_tool_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class ToolUseContext(BaseModel):
    """工具执行的共享运行环境（控制总线）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    working_dir: str = "."
    message_history: list[Any] = []
    mcp_clients: dict[str, Any] = {}
    app_state: dict[str, Any] = {}
    extra: dict[str, Any] = {}


ToolHandler = Callable[[dict[str, Any], ToolUseContext], Awaitable[ToolResult]]
