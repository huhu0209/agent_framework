"""memory_search 工具测试。"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.search import handle_memory_search
from agent_framework.memory.types import EventType
from agent_framework.tools.types import ToolUseContext


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


@pytest.fixture
def ctx(memory_dir: Path) -> ToolUseContext:
    return ToolUseContext(working_dir=str(memory_dir))


class TestMemorySearch:
    async def test_search_finds_event(self, memory_dir: Path, ctx: ToolUseContext):
        log_mgr = EpisodicLogManager(memory_dir=memory_dir)
        ts = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        await log_mgr.append(timestamp=ts, event_type=EventType.DECISION, content="用 FastAPI 框架")

        ctx.extra["memory_dir"] = str(memory_dir)
        result = await handle_memory_search({"query": "FastAPI", "top_k": 5}, ctx)

        assert not result.is_error
        assert "FastAPI" in result.content

    async def test_search_no_results(self, memory_dir: Path, ctx: ToolUseContext):
        ctx.extra["memory_dir"] = str(memory_dir)
        result = await handle_memory_search({"query": "不存在的关键词", "top_k": 5}, ctx)

        assert not result.is_error

    async def test_search_no_memory_dir(self, tmp_path: Path):
        ctx = ToolUseContext(working_dir=str(tmp_path))
        result = await handle_memory_search({"query": "test"}, ctx)

        assert result.is_error
        assert "未配置" in result.content

    async def test_search_returns_full_event_block(self, memory_dir: Path, ctx: ToolUseContext):
        log_mgr = EpisodicLogManager(memory_dir=memory_dir)
        ts = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        await log_mgr.append(timestamp=ts, event_type=EventType.DECISION, content="用 FastAPI 框架")

        ctx.extra["memory_dir"] = str(memory_dir)
        result = await handle_memory_search({"query": "FastAPI", "top_k": 5}, ctx)

        assert not result.is_error
        assert "FastAPI" in result.content
        assert "14:32" in result.content or "决策" in result.content
