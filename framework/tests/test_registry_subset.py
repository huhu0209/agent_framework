"""Tests for ToolRegistry.subset()."""

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolSpec


def _make_spec(name: str) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"{name} tool",
        parameters=ToolParameterSchema(),
        handler=lambda args, ctx: None,
    )


def test_subset_returns_only_named_tools() -> None:
    reg = ToolRegistry()
    reg.register(_make_spec("a"))
    reg.register(_make_spec("b"))
    reg.register(_make_spec("c"))

    sub = reg.subset({"a", "c"})

    assert set(sub.list_tools()) == {"a", "c"}


def test_subset_ignores_missing_names() -> None:
    reg = ToolRegistry()
    reg.register(_make_spec("a"))

    sub = reg.subset({"a", "nonexistent"})

    assert sub.list_tools() == ["a"]


def test_subset_empty_set() -> None:
    reg = ToolRegistry()
    reg.register(_make_spec("a"))

    sub = reg.subset(set())

    assert sub.list_tools() == []


def test_subset_does_not_affect_original() -> None:
    reg = ToolRegistry()
    reg.register(_make_spec("a"))
    reg.register(_make_spec("b"))

    sub = reg.subset({"a"})

    assert reg.list_tools() == ["a", "b"]
    assert sub.list_tools() == ["a"]
