"""memory_write 工具测试。"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.types import EventType
from agent_framework.tools.builtin.memory_tools import handle_memory_write
from agent_framework.tools.types import ToolUseContext


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


@pytest.fixture
def ctx(memory_dir: Path) -> ToolUseContext:
    c = ToolUseContext(working_dir=str(memory_dir))
    c.extra["memory_dir"] = str(memory_dir)
    return c


class TestMemoryWrite:
    async def test_write_creates_log_entry(self, memory_dir: Path, ctx: ToolUseContext):
        result = await handle_memory_write(
            {"event_type": "决策", "content": "选择 PostgreSQL 作为主数据库"},
            ctx,
        )

        assert not result.is_error
        assert "已记录" in result.content

        log_mgr = EpisodicLogManager(memory_dir=memory_dir)
        today = datetime.now().strftime("%Y-%m-%d")
        log_content = await log_mgr.read_log(today)

        assert log_content is not None
        assert "PostgreSQL" in log_content
        assert "决策" in log_content

    async def test_write_all_event_types(self, memory_dir: Path, ctx: ToolUseContext):
        for et in ("决策", "偏好", "错误", "约定", "进展"):
            result = await handle_memory_write(
                {"event_type": et, "content": f"测试 {et}"},
                ctx,
            )
            assert not result.is_error, f"{et} should succeed"

    async def test_write_invalid_event_type(self, ctx: ToolUseContext):
        result = await handle_memory_write(
            {"event_type": "invalid", "content": "test"},
            ctx,
        )

        assert result.is_error
        assert "可选值" in result.content

    async def test_write_empty_content(self, ctx: ToolUseContext):
        result = await handle_memory_write(
            {"event_type": "决策", "content": "   "},
            ctx,
        )

        assert result.is_error
        assert "不能为空" in result.content

    async def test_write_no_memory_dir(self, tmp_path: Path):
        ctx = ToolUseContext(working_dir=str(tmp_path))
        result = await handle_memory_write(
            {"event_type": "决策", "content": "test"},
            ctx,
        )

        assert result.is_error
        assert "未配置" in result.content
