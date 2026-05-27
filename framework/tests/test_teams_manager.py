"""TeamManager 测试。"""

import asyncio
import pytest

from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.teams.bus import MessageBus
from agent_framework.teams.manager import TeamManager
from agent_framework.teams.types import TeammateConfig, TeammateStatus
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


@pytest.fixture
def team_mgr(tmp_path):
    adapter = FakeAdapter()
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    bus = MessageBus(tmp_path)
    return TeamManager(
        team_dir=tmp_path, bus=bus,
        adapter=adapter, router=router, ctx=ctx,
    )


@pytest.mark.asyncio
async def test_spawn_creates_teammate(team_mgr):
    config = TeammateConfig(name="alice", role="researcher", system_prompt="研究员")
    await team_mgr.spawn(config)

    assert "alice" in team_mgr._statuses
    assert team_mgr._statuses["alice"] == TeammateStatus.IDLE


@pytest.mark.asyncio
async def test_spawn_and_shutdown(team_mgr):
    config = TeammateConfig(
        name="bob", role="worker", system_prompt="工人",
        max_idle_seconds=60,
    )
    await team_mgr.spawn(config)
    await team_mgr.shutdown("bob")

    await asyncio.sleep(0.5)

    assert team_mgr._statuses["bob"] == TeammateStatus.SHUTDOWN


@pytest.mark.asyncio
async def test_list_all_shows_teammates(team_mgr):
    await team_mgr.spawn(TeammateConfig(name="alice", role="r", system_prompt="R"))
    await team_mgr.spawn(TeammateConfig(name="bob", role="w", system_prompt="W"))

    board = team_mgr.list_all()
    assert "alice" in board
    assert "bob" in board


@pytest.mark.asyncio
async def test_teammate_processes_message(team_mgr, tmp_path):
    config = TeammateConfig(name="alice", role="researcher", system_prompt="研究员")
    await team_mgr.spawn(config)

    bus = team_mgr._bus
    bus.send("lead", "alice", "搜索文件")

    await asyncio.sleep(1)

    assert team_mgr._statuses["alice"] in (TeammateStatus.IDLE, TeammateStatus.WORKING)
