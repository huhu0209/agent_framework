"""AgentLoop.resume 测试 — 有状态对话续跑。"""

import pytest

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


class TrackingAdapter:
    def __init__(self):
        self.calls: list[int] = []

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        self.calls.append(len(config.messages))
        return CompletionResult(
            id="fake", model=config.model,
            content=[TextBlock(text=f"收到 {len(config.messages)} 条消息")],
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


@pytest.mark.asyncio
async def test_resume_appends_to_existing_messages():
    adapter = TrackingAdapter()
    loop = AgentLoop(
        adapter=adapter, model="fake",
        router=ToolRouter(ToolRegistry()), ctx=ToolUseContext(),
    )

    # First run — fresh (system + user = 2 messages)
    async for event in loop.run("第一轮"):
        pass
    assert adapter.calls == [2]

    # Second run — resume (appends user to existing messages)
    async for event in loop.run("第二轮", resume=True):
        pass
    # After first run: [system, user, assistant] = 3
    # Resume appends user: [system, user, assistant, user] = 4
    assert adapter.calls == [2, 4]


@pytest.mark.asyncio
async def test_resume_false_resets_messages():
    adapter = TrackingAdapter()
    loop = AgentLoop(
        adapter=adapter, model="fake",
        router=ToolRouter(ToolRegistry()), ctx=ToolUseContext(),
    )

    async for event in loop.run("第一轮"):
        pass
    async for event in loop.run("第二轮"):
        pass  # Default resume=False, fresh start

    assert adapter.calls == [2, 2]


@pytest.mark.asyncio
async def test_resume_on_empty_messages_same_as_fresh():
    adapter = TrackingAdapter()
    loop = AgentLoop(
        adapter=adapter, model="fake",
        router=ToolRouter(ToolRegistry()), ctx=ToolUseContext(),
    )

    async for event in loop.run("第一轮", resume=True):
        pass
    # resume=True but _messages is empty → falls through to fresh init
    assert adapter.calls == [2]
