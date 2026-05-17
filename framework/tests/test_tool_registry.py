"""ToolRegistry 测试。"""

import pytest
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolResult, ToolSpec
from agent_framework.llm.types import ToolDefinition, ToolParameterSchema


async def _fake_handler(args, ctx):
    return ToolResult(content="ok")


def _make_spec(name: str = "test_tool", **kwargs) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"{name} description",
        parameters=ToolParameterSchema(),
        handler=_fake_handler,
        **kwargs,
    )


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        spec = _make_spec("read_file")
        registry.register(spec)

        assert registry.get("read_file") is spec

    def test_get_nonexistent_returns_none(self):
        registry = ToolRegistry()
        assert registry.get("no_such_tool") is None

    def test_register_duplicate_raises(self):
        registry = ToolRegistry()
        registry.register(_make_spec("dup"))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_make_spec("dup"))

    def test_get_definitions(self):
        registry = ToolRegistry()
        registry.register(_make_spec("tool_a"))
        registry.register(_make_spec("tool_b"))

        defs = registry.get_definitions()
        assert len(defs) == 2
        assert all(isinstance(d, ToolDefinition) for d in defs)
        names = {d.name for d in defs}
        assert names == {"tool_a", "tool_b"}

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(_make_spec("alpha"))
        registry.register(_make_spec("beta"))

        assert set(registry.list_tools()) == {"alpha", "beta"}

    def test_empty_registry(self):
        registry = ToolRegistry()
        assert registry.list_tools() == []
        assert registry.get_definitions() == []
        assert registry.get("anything") is None
