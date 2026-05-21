"""每日日志管理器测试。"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.types import EventType


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


@pytest.fixture
def manager(memory_dir: Path) -> EpisodicLogManager:
    return EpisodicLogManager(memory_dir=memory_dir)


class TestEpisodicLogManager:
    def test_append_creates_file(self, manager: EpisodicLogManager, memory_dir: Path):
        ts = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        manager.append(timestamp=ts, event_type=EventType.DECISION, content="做了一个决策")

        log_file = memory_dir / "logs" / "2026" / "05" / "2026-05-20.md"
        assert log_file.exists()

        content = log_file.read_text(encoding="utf-8")
        assert "## [14:32] 决策" in content
        assert "做了一个决策" in content

    def test_append_adds_to_existing(self, manager: EpisodicLogManager, memory_dir: Path):
        ts1 = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        ts2 = datetime(2026, 5, 20, 15, 10, tzinfo=timezone.utc)

        manager.append(timestamp=ts1, event_type=EventType.DECISION, content="第一个")
        manager.append(timestamp=ts2, event_type=EventType.ERROR, content="第二个")

        log_file = memory_dir / "logs" / "2026" / "05" / "2026-05-20.md"
        content = log_file.read_text(encoding="utf-8")
        assert "## [14:32] 决策" in content
        assert "## [15:10] 错误" in content

    def test_read_log_exists(self, manager: EpisodicLogManager, memory_dir: Path):
        ts = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        manager.append(timestamp=ts, event_type=EventType.PROGRESS, content="完成了一步")

        content = manager.read_log(date="2026-05-20")
        assert content is not None
        assert "完成了一步" in content

    def test_read_log_not_exists(self, manager: EpisodicLogManager):
        content = manager.read_log(date="2020-01-01")
        assert content is None

    def test_list_dates(self, manager: EpisodicLogManager, memory_dir: Path):
        ts1 = datetime(2026, 5, 19, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)

        manager.append(timestamp=ts1, event_type=EventType.PROGRESS, content="a")
        manager.append(timestamp=ts2, event_type=EventType.PROGRESS, content="b")

        dates = manager.list_dates()
        assert "2026-05-19" in dates
        assert "2026-05-20" in dates
