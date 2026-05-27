"""Team 工具测试。"""

import pytest

from agent_framework.llm.types import (
    CompletionConfig, CompletionResult, StopReason,
    TextBlock, UsageStats,
)
from agent_framework.teams.bus import MessageBus
from agent_framework.teams.manager import TeamManager
from agent_framework.teams.tools import create_team_tools
from agent_framework.teams.types import TeammateConfig
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


class FakeAdapter:
    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="fake", model=config.model,
            content=[TextBlock(text="完成")],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=10, output_tokens=5),
        )

    def get_max_context_tokens(self) -> int:
        return 128000

    def get_provider_info(self):
        from agent_framework.llm.types import ProviderInfo
        return ProviderInfo(
            name="fake", base_url="https://fake",
            default_model="fake-model", max_context_tokens=128000,
        )


def _make_team_mgr(tmp_path):
    adapter = FakeAdapter()
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    bus = MessageBus(tmp_path)
    mgr = TeamManager(
        team_dir=tmp_path, bus=bus,
        adapter=adapter, router=router, ctx=ctx,
    )
    return mgr, bus, ctx


def test_create_team_tools_returns_five(tmp_path):
    mgr, bus, ctx = _make_team_mgr(tmp_path)
    tools = create_team_tools(mgr, bus)
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {"spawn_teammate", "list_teammates", "send_message", "read_inbox", "broadcast"}


@pytest.mark.asyncio
async def test_spawn_teammate_tool(tmp_path):
    mgr, bus, ctx = _make_team_mgr(tmp_path)
    tools = create_team_tools(mgr, bus)
    spawn_tool = next(t for t in tools if t.name == "spawn_teammate")

    result = await spawn_tool.handler(
        {"name": "alice", "role": "researcher", "system_prompt": "研究员"},
        ctx,
    )
    assert "alice" in result.content
    assert not result.is_error


@pytest.mark.asyncio
async def test_send_message_tool(tmp_path):
    mgr, bus, ctx = _make_team_mgr(tmp_path)
    tools = create_team_tools(mgr, bus)
    send_tool = next(t for t in tools if t.name == "send_message")

    result = await send_tool.handler(
        {"to": "alice", "content": "你好"},
        ctx,
    )
    assert "已发送" in result.content

    inbox = bus.read_inbox("alice")
    assert len(inbox) == 1
    assert inbox[0].content == "你好"


@pytest.mark.asyncio
async def test_read_inbox_uses_teammate_identity(tmp_path):
    mgr, bus, ctx = _make_team_mgr(tmp_path)
    ctx_with_id = ToolUseContext(extra={"teammate_name": "alice"})
    bus.send("lead", "alice", "消息内容")

    tools = create_team_tools(mgr, bus)
    read_tool = next(t for t in tools if t.name == "read_inbox")

    result = await read_tool.handler({}, ctx_with_id)
    assert "消息内容" in result.content


@pytest.mark.asyncio
async def test_broadcast_tool(tmp_path):
    mgr, bus, ctx = _make_team_mgr(tmp_path)
    # spawn a teammate first so broadcast has targets
    await mgr.spawn(TeammateConfig(name="bob", role="w", system_prompt="W"))

    tools = create_team_tools(mgr, bus)
    bc_tool = next(t for t in tools if t.name == "broadcast")

    result = await bc_tool.handler({"content": "同步中"}, ctx)
    assert "广播" in result.content or "broadcast" in result.content.lower()
