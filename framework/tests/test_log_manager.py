"""每日日志管理器测试。"""

from datetime import datetime, timezone

import pytest

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.types import EventType


@pytest.fixture
def log_mgr(memory_dir):
    return EpisodicLogManager(memory_dir=memory_dir)


class TestAppend:
    def test_creates_file_and_directories(self, log_mgr, memory_dir):
        ts = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        log_mgr.append(ts, EventType.DECISION, "选择 FastAPI")
        log_path = memory_dir / "logs" / "2026" / "05" / "2026-05-20.md"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "14:32" in content
        assert "决策" in content
        assert "选择 FastAPI" in content

    def test_multiple_appends_same_day(self, log_mgr):
        ts1 = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        log_mgr.append(ts1, EventType.PROGRESS, "完成 A")
        log_mgr.append(ts2, EventType.ERROR, "出错 B")
        content = log_mgr.read_log("2026-05-20")
        assert content is not None
        assert "10:00" in content
        assert "14:32" in content


class TestReadLog:
    def test_existing_log(self, log_mgr):
        ts = datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc)
        log_mgr.append(ts, EventType.DECISION, "test")
        assert log_mgr.read_log("2026-05-20") is not None

    def test_missing_log_returns_none(self, log_mgr):
        assert log_mgr.read_log("2020-01-01") is None


class TestWriteRaw:
    def test_raw_append(self, log_mgr):
        log_mgr.write_raw("2026-05-20", "## [14:32] 决策\n内容\n")
        content = log_mgr.read_log("2026-05-20")
        assert "14:32" in content


class TestListDates:
    def test_lists_sorted_dates(self, log_mgr):
        for day in [15, 10, 20]:
            ts = datetime(2026, 5, day, 12, 0, tzinfo=timezone.utc)
            log_mgr.append(ts, EventType.PROGRESS, f"day {day}")
        dates = log_mgr.list_dates()
        assert dates == ["2026-05-10", "2026-05-15", "2026-05-20"]

    def test_empty_dir_returns_empty(self, memory_dir):
        mgr = EpisodicLogManager(memory_dir=memory_dir)
        assert mgr.list_dates() == []


class TestValidation:
    def test_invalid_date_format(self, log_mgr):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            log_mgr._log_path("today")

    def test_invalid_date_empty(self, log_mgr):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            log_mgr._log_path("")
