"""Memory Flush 测试。"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_framework.llm.types import CompletionConfig, CompletionResult, StopReason, TextBlock, UsageStats
from agent_framework.memory.flush import FlushExtractor
from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.types import EventType


class MockAdapter:
    """最小 mock adapter。"""

    def __init__(self, response_text: str) -> None:
        self._response = response_text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="test-id",
            model=config.model,
            content=[TextBlock(text=self._response)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=100, output_tokens=50),
        )


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


class TestFlushExtractor:
    async def test_extract_events_with_results(self, memory_dir: Path):
        adapter = MockAdapter(
            "## [14:32] 决策\n用户要求测试用真实数据库。\n原因：之前 mock 导致生产失败。\n"
        )
        log_manager = EpisodicLogManager(memory_dir=memory_dir)
        extractor = FlushExtractor(adapter=adapter, model="test-model")

        events_text = await extractor.extract(
            conversation_text="用户: 测试用真实数据库\n助手: 好的",
            current_time=datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc),
        )

        assert events_text is not None
        assert "决策" in events_text

    async def test_extract_no_events(self, memory_dir: Path):
        adapter = MockAdapter("NO_EVENTS")
        log_manager = EpisodicLogManager(memory_dir=memory_dir)
        extractor = FlushExtractor(adapter=adapter, model="test-model")

        events_text = await extractor.extract(
            conversation_text="用户: 你好\n助手: 你好",
            current_time=datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc),
        )

        assert events_text is None

    async def test_flush_writes_to_daily_log(self, memory_dir: Path):
        adapter = MockAdapter("## [14:32] 决策\n做了一个决策\n")
        log_manager = EpisodicLogManager(memory_dir=memory_dir)
        extractor = FlushExtractor(adapter=adapter, model="test-model")

        now = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        result = await extractor.flush(
            conversation_text="做了一些讨论",
            current_time=now,
            log_manager=log_manager,
        )

        assert result is True
        log_content = log_manager.read_log("2026-05-20")
        assert log_content is not None
        assert "决策" in log_content

    async def test_flush_no_events_skips_write(self, memory_dir: Path):
        adapter = MockAdapter("NO_EVENTS")
        log_manager = EpisodicLogManager(memory_dir=memory_dir)
        extractor = FlushExtractor(adapter=adapter, model="test-model")

        now = datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc)
        result = await extractor.flush(
            conversation_text="闲聊",
            current_time=now,
            log_manager=log_manager,
        )

        assert result is False
        assert log_manager.read_log("2026-05-20") is None
