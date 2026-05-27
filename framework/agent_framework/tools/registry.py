"""工具注册表 — name -> ToolSpec 的 dispatch map。"""

from __future__ import annotations

from agent_framework.llm.types import ToolDefinition
from agent_framework.tools.types import ToolSpec


class ToolRegistry:
    """工具注册表。加工具 = register(spec)，循环永远不改。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' already registered")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def get_definitions(self) -> list[ToolDefinition]:
        return [spec.to_tool_definition() for spec in self._tools.values()]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def subset(self, names: set[str]) -> ToolRegistry:
        sub = ToolRegistry()
        for name in names:
            spec = self.get(name)
            if spec:
                sub.register(spec)
        return sub
