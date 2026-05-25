"""MEMORY.md 索引管理器测试。"""

import pytest

from agent_framework.memory.index_manager import MemoryIndexManager, _MAX_LINES, _MAX_LINE_LENGTH


@pytest.fixture
def index_mgr(tmp_path):
    return MemoryIndexManager(tmp_path / "MEMORY.md")


class TestUpdate:
    def test_creates_new_file(self, index_mgr):
        index_mgr.update("user_style.md", "用户风格", "偏好详细解释")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "[用户风格](user_style.md)" in content
        assert "偏好详细解释" in content

    def test_replaces_existing_entry(self, index_mgr):
        index_mgr.update("user_style.md", "用户风格", "旧描述")
        index_mgr.update("user_style.md", "用户风格", "新描述")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "新描述" in content
        assert "旧描述" not in content

    def test_truncates_long_line(self, index_mgr):
        long_desc = "x" * 200
        index_mgr.update("file.md", "name", long_desc)
        content = index_mgr._path.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if l.startswith("- ")]
        assert len(lines[0]) <= _MAX_LINE_LENGTH


class TestRemove:
    def test_removes_existing_entry(self, index_mgr):
        index_mgr.update("file.md", "name", "desc")
        index_mgr.remove("file.md")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "file.md" not in content

    def test_remove_nonexistent_is_noop(self, index_mgr):
        index_mgr.update("a.md", "A", "desc a")
        index_mgr.remove("b.md")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "a.md" in content


class TestTruncation:
    def test_preserves_header_on_truncation(self, tmp_path):
        index_path = tmp_path / "MEMORY.md"
        header = "# Memory Index\n\n"
        index_path.write_text(header, encoding="utf-8")
        mgr = MemoryIndexManager(index_path)
        for i in range(_MAX_LINES + 10):
            mgr.update(f"file_{i}.md", f"name {i}", f"desc {i}")
        content = index_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        assert any(l.startswith("# Memory Index") for l in lines)
