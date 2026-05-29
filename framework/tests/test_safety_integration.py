"""安全边界集成测试 — AgentLoop → ToolRouter → safe_path 全链路。"""

import pytest
from unittest.mock import AsyncMock

from agent_framework.agents.agent_loop import AgentLoop, LoopEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    ToolUseBlock,
    UsageStats,
)
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


def _make_mock_adapter() -> AsyncMock:
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    return adapter


def _text_result(text: str) -> CompletionResult:
    return CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(),
    )


def _tool_use_result(*tool_calls: ToolUseBlock) -> CompletionResult:
    return CompletionResult(
        id="test-id",
        content=list(tool_calls),
        model="mock",
        stop_reason=StopReason.TOOL_USE,
        usage=UsageStats(),
    )


def _make_tool(name: str, id_: str = "tc_1", **input_kwargs) -> ToolUseBlock:
    return ToolUseBlock(id=id_, name=name, input=input_kwargs)


async def _collect_events(loop: AgentLoop, message: str) -> list[LoopEvent]:
    return [event async for event in loop.run(message)]


@pytest.mark.asyncio
async def test_path_traversal_rejected(tmp_path):
    """路径遍历攻击 (../../) 被全链路拒绝。"""
    (tmp_path / "safe.txt").write_text("safe content", encoding="utf-8")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="../../../etc/passwd")),
        _text_result("ok"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "路径访问被拒绝" in tool_events[0].data["tool_results"][0]
    assert adapter.complete.call_count == 2


@pytest.mark.asyncio
async def test_absolute_path_rejected(tmp_path):
    """绝对路径 (/etc/passwd) 被全链路拒绝。"""
    (tmp_path / "safe.txt").write_text("safe content", encoding="utf-8")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="/etc/passwd")),
        _text_result("ok"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "路径访问被拒绝" in tool_events[0].data["tool_results"][0]
    assert adapter.complete.call_count == 2


@pytest.mark.asyncio
async def test_normal_file_access_allowed(tmp_path):
    """正常文件访问（工作目录内）成功。"""
    (tmp_path / "safe.txt").write_text("safe content", encoding="utf-8")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="safe.txt")),
        _text_result("done"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "safe content" in tool_events[0].data["tool_results"][0]
    assert all(
        "路径访问被拒绝" not in e.data.get("tool_results", [""])[0]
        for e in events
        if e.type == "tool_result"
    )
