"""ToolRouter 测试 — 来源分叉。"""

import pytest
from app.core.tools.router import ToolRouter
from app.core.tools.registry import ToolRegistry
from app.core.tools.types import ToolCall, ToolResult, ToolSpec, ToolUseContext
from app.core.llm.types import ToolParameterSchema


async def _echo_handler(args, ctx):
    return ToolResult(content=f"echo: {args.get('msg', '')}")


def _make_registry_with_echo() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="echo",
        description="echo tool",
        parameters=ToolParameterSchema(
            properties={"msg": {"type": "string"}},
            required=["msg"],
        ),
        handler=_echo_handler,
    ))
    return registry


ctx = ToolUseContext()


@pytest.mark.asyncio
async def test_builtin_dispatch():
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_1", name="echo", arguments={"msg": "hello"}),
        ctx,
    )
    assert result.content == "echo: hello"
    assert result.is_error is False


@pytest.mark.asyncio
async def test_unknown_builtin_returns_error():
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_2", name="nonexistent", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未知工具" in result.content


@pytest.mark.asyncio
async def test_mcp_prefix_returns_not_connected():
    """MCP 工具路由已预留，但未连接时返回错误。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_3", name="mcp__github__create_issue", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未连接" in result.content


@pytest.mark.asyncio
async def test_agent_prefix_returns_not_implemented():
    """Agent-as-tool 路由已预留，返回未实现。"""
    registry = _make_registry_with_echo()
    router = ToolRouter(registry)
    result = await router.dispatch(
        ToolCall(id="tc_4", name="agent__coder", arguments={}),
        ctx,
    )
    assert result.is_error is True
    assert "未实现" in result.content
