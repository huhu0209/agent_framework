"""Tests for ToolRouter.derive() — child router with inherited infrastructure."""

import pytest

from agent_framework.prompts.profiles import AgentProfile
from agent_framework.safety.permissions import PermissionPipeline
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolParameterSchema, ToolResult, ToolSpec


def _make_spec(name: str) -> ToolSpec:
    """Create a minimal ToolSpec with an async handler."""
    async def handler(args, ctx):  # type: ignore[no-untyped-def]
        return ToolResult(content=f"{name} called")

    return ToolSpec(
        name=name,
        description=f"{name} tool",
        parameters=ToolParameterSchema(type="object", properties={}, required=[]),
        handler=handler,
    )


def _make_registry(*names: str) -> ToolRegistry:
    """Create a registry pre-loaded with specs for the given names."""
    reg = ToolRegistry()
    for name in names:
        reg.register(_make_spec(name))
    return reg


class TestDeriveCreatesChildWithSubsetRegistry:
    """derive() creates a child router whose registry is a subset of the parent's."""

    def test_derive_creates_child_with_subset_registry(self) -> None:
        parent_reg = _make_registry("read", "write")
        parent = ToolRouter(registry=parent_reg)

        child_reg = _make_registry("read")
        child = parent.derive(child_reg)

        assert child is not parent
        assert child.registry is child_reg
        assert parent.registry is parent_reg
        # child only has "read"
        assert child.registry.get("read") is not None
        assert child.registry.get("write") is None


class TestDeriveInheritsPermissionPipeline:
    """derive() propagates the permission pipeline to the child."""

    def test_derive_inherits_permission_pipeline(self) -> None:
        parent = ToolRouter(registry=_make_registry("read"))

        profile = AgentProfile(name="test", description="test", permission_mode="accept")
        pipeline = PermissionPipeline(profile)
        parent.set_permission_pipeline(pipeline)

        child = parent.derive(_make_registry("read"))

        assert child._permission_pipeline is pipeline


class TestDeriveChildIndependentOfParent:
    """Adding a tool to the child's registry does not affect the parent."""

    def test_derive_child_independent_of_parent(self) -> None:
        parent_reg = _make_registry("read")
        parent = ToolRouter(registry=parent_reg)

        child_reg = _make_registry("read")
        child = parent.derive(child_reg)

        # Add a tool only to the child
        child_reg.register(_make_spec("extra"))

        assert parent.registry.get("extra") is None
        assert child.registry.get("extra") is not None
