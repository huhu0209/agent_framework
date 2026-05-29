"""TeamManager 测试。"""

import asyncio
import time

import pytest
from unittest.mock import AsyncMock, patch

from agent_framework.agents.agent_loop import LoopEvent
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


# ---------------------------------------------------------------------------
# _loop 行为深度测试
# ---------------------------------------------------------------------------


def _make_loop_mock(events=None):
    """创建 mock AgentLoop 类，yield 预设事件。"""
    if events is None:
        events = [LoopEvent(type="done", step=1, data={})]

    class MockAgentLoop:
        def __init__(self, **kwargs):
            self._kwargs = kwargs
            self._events = list(events)

        async def run(self, prompt, plan=None, *, resume=False):
            for event in self._events:
                yield event

    return MockAgentLoop


async def _wait_task(task, timeout=2.0):
    """等待后台 _loop task 完成，超时则取消。"""
    try:
        await asyncio.wait_for(task, timeout=timeout)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestTeamLoop:
    """TeamManager._loop 行为测试。"""

    @pytest.mark.asyncio
    async def test_shutdown_via_inbox(self, team_mgr):
        """收到 shutdown_request inbox 消息后正确退出并设置 SHUTDOWN 状态。"""
        mock_loop_cls = _make_loop_mock()

        with patch("agent_framework.teams.manager.AgentLoop", mock_loop_cls), \
             patch("agent_framework.teams.manager.asyncio.sleep", new_callable=AsyncMock):

            # 先发 shutdown_request，再 spawn —— _loop 第一轮就能读到
            config = TeammateConfig(name="carol", role="analyst", system_prompt="分析师")
            team_mgr._bus.send("lead", "carol", "请关闭", msg_type="shutdown_request")
            await team_mgr.spawn(config)

            # 等待 _loop task 完成
            await _wait_task(team_mgr._tasks["carol"])

        assert team_mgr._statuses["carol"] == TeammateStatus.SHUTDOWN

    @pytest.mark.asyncio
    async def test_idle_timeout_shutdown(self, team_mgr):
        """idle 超过 max_idle_seconds 后自动关闭。"""
        mock_loop_cls = _make_loop_mock()

        # 提供足够多的值：idle_start + 每次 idle check 各一次
        # 第一次 monotonic → idle_start (0.0)
        # 之后每次循环 → idle check，值递增直到超过阈值
        monotonic_values = iter([0.0, 100.0, 200.0, 300.0, 400.0])

        def fake_monotonic():
            try:
                return next(monotonic_values)
            except StopIteration:
                return 999.0

        with patch("agent_framework.teams.manager.AgentLoop", mock_loop_cls), \
             patch("agent_framework.teams.manager.asyncio.sleep", new_callable=AsyncMock), \
             patch("agent_framework.teams.manager.time.monotonic", side_effect=fake_monotonic):

            config = TeammateConfig(
                name="dave", role="helper", system_prompt="助手",
                max_idle_seconds=1,
            )
            await team_mgr.spawn(config)

            await _wait_task(team_mgr._tasks["dave"])

        assert team_mgr._statuses["dave"] == TeammateStatus.SHUTDOWN

    @pytest.mark.asyncio
    async def test_status_transitions(self, team_mgr):
        """处理 inbox 时状态经历 IDLE -> WORKING -> IDLE 转换。"""
        observed_statuses = []

        class TrackingDict(dict):
            """dict 子类，记录所有赋值操作。"""
            def __setitem__(self, key, value):
                if key == "diana":
                    observed_statuses.append(value)
                super().__setitem__(key, value)

        mock_loop_cls = _make_loop_mock()

        with patch("agent_framework.teams.manager.AgentLoop", mock_loop_cls), \
             patch("agent_framework.teams.manager.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            call_count = 0

            async def sleep_then_shutdown(n):
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    team_mgr._bus.send("lead", "diana", "关闭", msg_type="shutdown_request")

            mock_sleep.side_effect = sleep_then_shutdown

            # 替换 _statuses 为跟踪 dict
            tracking = TrackingDict(team_mgr._statuses)
            team_mgr._statuses = tracking

            config = TeammateConfig(name="diana", role="researcher", system_prompt="研究员")
            team_mgr._bus.send("lead", "diana", "分析报告")
            await team_mgr.spawn(config)

            await _wait_task(team_mgr._tasks["diana"])

        # 经历 IDLE (spawn) -> WORKING (处理消息) -> IDLE (处理完成) -> SHUTDOWN
        assert TeammateStatus.WORKING in observed_statuses
        assert TeammateStatus.IDLE in observed_statuses
        assert TeammateStatus.SHUTDOWN in observed_statuses

    @pytest.mark.asyncio
    async def test_notification_emitted_on_shutdown(self, team_mgr):
        """关闭时向 notifications queue 发送 TeamNotification。"""
        mock_loop_cls = _make_loop_mock()

        with patch("agent_framework.teams.manager.AgentLoop", mock_loop_cls), \
             patch("agent_framework.teams.manager.asyncio.sleep", new_callable=AsyncMock):

            config = TeammateConfig(name="eve", role="worker", system_prompt="工人")
            team_mgr._bus.send("lead", "eve", "关闭", msg_type="shutdown_request")
            await team_mgr.spawn(config)

            await _wait_task(team_mgr._tasks["eve"])

        assert not team_mgr.notifications.empty()
        notification = team_mgr.notifications.get_nowait()
        assert notification.name == "eve"
        assert notification.status == "shutdown"

    @pytest.mark.asyncio
    async def test_inbox_processing_formats_prompt(self, team_mgr):
        """发送 2 条消息后，AgentLoop.run 收到的 prompt 包含正确的 inbox 格式。"""
        captured_prompts = []

        def make_capturing_mock():
            class CapturingLoop:
                def __init__(self, **kwargs):
                    pass

                async def run(self, prompt, plan=None, *, resume=False):
                    captured_prompts.append(prompt)
                    yield LoopEvent(type="done", step=1, data={})

            return CapturingLoop

        with patch("agent_framework.teams.manager.AgentLoop", make_capturing_mock()), \
             patch("agent_framework.teams.manager.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            call_count = 0

            async def sleep_then_shutdown(n):
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    team_mgr._bus.send("lead", "frank", "关闭", msg_type="shutdown_request")

            mock_sleep.side_effect = sleep_then_shutdown

            config = TeammateConfig(name="frank", role="analyst", system_prompt="分析师")
            # 先发 2 条消息，_loop 第一轮就能读到
            team_mgr._bus.send("lead", "frank", "消息一")
            team_mgr._bus.send("lead", "frank", "消息二")
            await team_mgr.spawn(config)

            await _wait_task(team_mgr._tasks["frank"])

        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "<inbox from='lead'>" in prompt
        assert "消息一" in prompt
        assert "消息二" in prompt
