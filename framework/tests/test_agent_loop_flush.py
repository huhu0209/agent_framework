"""AgentLoop flush 集成测试 — 验证 compaction 前自动 flush 情景记忆。"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    ProviderInfo,
    StopReason,
    SystemMessage,
    TextBlock,
    UsageStats,
    UserMessage,
)
from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

from conftest import MockAdapter


def _make_flush_loop(adapter=None, memory_dir: Path | None = None, **kwargs):
    """创建启用 flush 的 AgentLoop。"""
    adapter = adapter or MockAdapter("回答")
    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    if memory_dir:
        ctx.extra["memory_dir"] = str(memory_dir)
    return AgentLoop(
        adapter, model="mock", router=router, ctx=ctx,
        memory_flush_enabled=True, **kwargs,
    )


def _make_long_messages(n: int = 25):
    """创建足够长的消息列表以触发 compaction。"""
    messages = [SystemMessage(content="test system")]
    for i in range(n):
        messages.append(UserMessage(content=[TextBlock(text=f"message {i} " * 100)]))
        messages.append(TextBlock(text=f"reply {i} " * 100) and UserMessage(content=[TextBlock(text="ok")]))
    return messages


@pytest.mark.asyncio
async def test_flush_triggers_on_compaction(memory_dir: Path):
    """compaction 触发时，flush 自动执行并写入每日日志。"""
    flush_adapter = MockAdapter("## [14:30] 决策\n选择了方案A\n")
    compact_adapter = MockAdapter("压缩后的摘要")

    loop = _make_flush_loop(
        flush_adapter, memory_dir=memory_dir, compact_adapter=compact_adapter,
    )
    messages = [SystemMessage(content="test")]

    with (
        patch("agent_framework.agents.agent_loop.should_compact", return_value=True),
        patch("agent_framework.agents.agent_loop.compact", return_value=[SystemMessage(content="compressed")]),
    ):
        result = await loop._maybe_compact(messages, step=1)

    log_mgr = EpisodicLogManager(memory_dir)
    today = datetime.now().strftime("%Y-%m-%d")
    log_content = await log_mgr.read_log(today)
    assert log_content is not None
    assert "决策" in log_content


@pytest.mark.asyncio
async def test_no_flush_when_disabled(memory_dir: Path):
    """memory_flush_enabled=False 时不创建 FlushExtractor。"""
    adapter = MockAdapter("回答")
    registry = create_builtin_registry()
    ctx = ToolUseContext()
    ctx.extra["memory_dir"] = str(memory_dir)

    loop = AgentLoop(
        adapter, model="mock", router=ToolRouter(registry), ctx=ctx,
        memory_flush_enabled=False,
    )

    assert loop._flush_extractor is None


@pytest.mark.asyncio
async def test_flush_failure_does_not_block_compaction(memory_dir: Path):
    """flush 失败时 compaction 仍然完成。"""
    failing_adapter = AsyncMock(spec=ILLMAdapter)
    failing_adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    failing_adapter.complete.side_effect = RuntimeError("flush LLM failed")

    loop = _make_flush_loop(
        failing_adapter, memory_dir=memory_dir,
        compact_adapter=MockAdapter("压缩后的摘要"),
    )
    messages = [SystemMessage(content="test")]

    with (
        patch("agent_framework.agents.agent_loop.should_compact", return_value=True),
        patch("agent_framework.agents.agent_loop.compact", return_value=[SystemMessage(content="compressed")]),
    ):
        result = await loop._maybe_compact(messages, step=1)

    assert result != messages


@pytest.mark.asyncio
async def test_no_flush_without_memory_dir():
    """无 memory_dir 时跳过 flush，compact 正常。"""
    loop = _make_flush_loop(memory_dir=None)

    messages = [SystemMessage(content="test")]
    with (
        patch("agent_framework.agents.agent_loop.should_compact", return_value=True),
        patch("agent_framework.agents.agent_loop.compact", return_value=[SystemMessage(content="compressed")]),
    ):
        result = await loop._maybe_compact(messages, step=1)

    assert result != messages


@pytest.mark.asyncio
async def test_no_flush_without_compaction(memory_dir: Path):
    """compaction 未触发时无 flush。"""
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )

    loop = _make_flush_loop(adapter, memory_dir=memory_dir)
    messages = [SystemMessage(content="test"), UserMessage(content=[TextBlock(text="hi")])]

    with patch("agent_framework.agents.agent_loop.should_compact", return_value=False):
        result = await loop._maybe_compact(messages, step=1)

    assert result == messages
    adapter.complete.assert_not_called()


@pytest.mark.asyncio
async def test_flush_reads_existing_log_for_dedup(memory_dir: Path):
    """flush 前读取当天已有日志，传入 extract 做去重。"""
    log_mgr = EpisodicLogManager(memory_dir)
    today = datetime.now().strftime("%Y-%m-%d")
    await log_mgr.write_raw(today, "## [10:00] 决策\n已有的决策\n")

    flush_adapter = AsyncMock(spec=ILLMAdapter)
    flush_adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    flush_adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text="## [14:30] 偏好\n新的偏好\n")],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(),
    )

    loop = _make_flush_loop(
        flush_adapter, memory_dir=memory_dir,
        compact_adapter=MockAdapter("压缩后的摘要"),
    )
    messages = [SystemMessage(content="test")]

    with (
        patch("agent_framework.agents.agent_loop.should_compact", return_value=True),
        patch("agent_framework.agents.agent_loop.compact", return_value=[SystemMessage(content="compressed")]),
    ):
        result = await loop._maybe_compact(messages, step=1)

    # flush_adapter.complete 被调用一次（flush LLM call）
    call_config = flush_adapter.complete.call_args[0][0]
    user_msg_text = call_config.messages[1].content[0].text
    assert "已有的决策" in user_msg_text
    assert "请勿重复提取" in user_msg_text
