"""Tool System 核心类型定义。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypedDict

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
    handler: Any = Field(default=None, exclude=True, repr=False)
    annotations: dict[str, Any] = {}

    def to_tool_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class ToolContextExtra(TypedDict, total=False):
    """已知 extra 键的类型提示（运行时仍为 dict[str, Any]）。

    handler 代码可通过 ``cast(ToolContextExtra, ctx.extra)`` 获得类型提示。
    """

    skill_registry: Any
    memory_dir: str
    memory_store: Any
    planning_session: Any
    worker_manager: Any


class ToolUseContext(BaseModel):
    """工具执行的共享运行环境（控制总线）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    working_dir: str = "."
    message_history: list[Any] = []
    mcp_clients: dict[str, Any] = {}
    app_state: dict[str, Any] = {}
    extra: dict[str, Any] = {}  # See ToolContextExtra for known keys


ToolHandler = Callable[[dict[str, Any], ToolUseContext], Awaitable[ToolResult]]
