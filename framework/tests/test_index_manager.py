"""MemoryIndexManager 测试。"""

from pathlib import Path

import pytest

from agent_framework.memory.index_manager import MemoryIndexManager


@pytest.fixture
def index_file(tmp_path: Path) -> Path:
    return tmp_path / "MEMORY.md"


class TestMemoryIndexManager:
    def test_update_creates_new_index(self, index_file: Path):
        manager = MemoryIndexManager(index_file)
        manager.update("feedback_testing.md", "测试策略", "测试用真实数据库")

        content = index_file.read_text(encoding="utf-8")
        assert "- [测试策略](feedback_testing.md) — 测试用真实数据库" in content

    def test_update_appends_second_entry(self, index_file: Path):
        manager = MemoryIndexManager(index_file)
        manager.update("feedback_testing.md", "测试策略", "测试用真实数据库")
        manager.update("user_profile.md", "用户偏好", "简洁回复")

        lines = index_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_update_existing_entry_replaces_summary(self, index_file: Path):
        manager = MemoryIndexManager(index_file)
        manager.update("feedback_testing.md", "测试策略", "旧描述")
        manager.update("feedback_testing.md", "测试策略", "新描述")

        content = index_file.read_text(encoding="utf-8")
        assert "新描述" in content
        assert "旧描述" not in content

    def test_update_truncates_at_200_lines(self, index_file: Path):
        manager = MemoryIndexManager(index_file)
        for i in range(205):
            manager.update(f"file_{i}.md", f"条目 {i}", f"描述 {i}")

        lines = index_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 200

    def test_remove_deletes_entry(self, index_file: Path):
        manager = MemoryIndexManager(index_file)
        manager.update("feedback_testing.md", "测试策略", "描述")
        manager.update("user_profile.md", "用户偏好", "偏好")

        manager.remove("feedback_testing.md")

        content = index_file.read_text(encoding="utf-8")
        assert "feedback_testing.md" not in content
        assert "user_profile.md" in content

    def test_update_truncates_description_at_150_chars(self, index_file: Path):
        manager = MemoryIndexManager(index_file)
        long_desc = "x" * 200
        manager.update("file.md", "名称", long_desc)

        lines = index_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines[0]) <= 150
