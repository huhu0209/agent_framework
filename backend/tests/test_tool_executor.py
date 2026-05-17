"""ToolExecutor 测试 — 超时、错误、截断。"""

import asyncio
import pytest
from app.core.tools.executor import ToolExecutor
from app.core.tools.types import ToolResult, ToolSpec, ToolUseContext
from app.core.llm.types import ToolParameterSchema


def _make_spec(handler, timeout_ms=30_000) -> ToolSpec:
    return ToolSpec(
        name="test_tool",
        description="test",
        parameters=ToolParameterSchema(),
        handler=handler,
        timeout_ms=timeout_ms,
    )


ctx = ToolUseContext()
executor = ToolExecutor()


@pytest.mark.asyncio
async def test_normal_execution():
    async def handler(args, ctx):
        return ToolResult(content="hello")

    spec = _make_spec(handler)
    result = await executor.execute(spec, {}, ctx)
    assert result.content == "hello"
    assert result.is_error is False


@pytest.mark.asyncio
async def test_timeout_returns_error():
    async def slow_handler(args, ctx):
        await asyncio.sleep(10)
        return ToolResult(content="never")

    spec = _make_spec(slow_handler, timeout_ms=50)
    result = await executor.execute(spec, {}, ctx)
    assert result.is_error is True
    assert "超时" in result.content


@pytest.mark.asyncio
async def test_exception_returns_error():
    async def bad_handler(args, ctx):
        raise FileNotFoundError("no such file")

    spec = _make_spec(bad_handler)
    result = await executor.execute(spec, {}, ctx)
    assert result.is_error is True
    assert "no such file" in result.content
    assert "建议" in result.content


@pytest.mark.asyncio
async def test_large_result_truncated():
    async def big_handler(args, ctx):
        return ToolResult(content="x" * 50_000)

    spec = _make_spec(big_handler)
    result = await executor.execute(spec, {}, ctx)
    assert result.is_error is False
    assert len(result.content) < 50_000
    assert "截断" in result.content
    assert result.metadata.get("truncated") is True


@pytest.mark.asyncio
async def test_small_result_not_truncated():
    async def small_handler(args, ctx):
        return ToolResult(content="short")

    spec = _make_spec(small_handler)
    result = await executor.execute(spec, {}, ctx)
    assert result.content == "short"
    assert result.metadata.get("truncated") is None
