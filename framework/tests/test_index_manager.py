"""MEMORY.md 索引管理器测试。"""

import pytest

from agent_framework.memory.index_manager import MemoryIndexManager, _MAX_LINES, _MAX_LINE_LENGTH


@pytest.fixture
def index_mgr(tmp_path):
    return MemoryIndexManager(tmp_path / "MEMORY.md")


class TestUpdate:
    async def test_creates_new_file(self, index_mgr):
        await index_mgr.update("user_style.md", "用户风格", "偏好详细解释")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "[用户风格](user_style.md)" in content
        assert "偏好详细解释" in content

    async def test_replaces_existing_entry(self, index_mgr):
        await index_mgr.update("user_style.md", "用户风格", "旧描述")
        await index_mgr.update("user_style.md", "用户风格", "新描述")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "新描述" in content
        assert "旧描述" not in content

    async def test_truncates_long_line(self, index_mgr):
        long_desc = "x" * 200
        await index_mgr.update("file.md", "name", long_desc)
        content = index_mgr._path.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if l.startswith("- ")]
        assert len(lines[0]) <= _MAX_LINE_LENGTH


class TestRemove:
    async def test_removes_existing_entry(self, index_mgr):
        await index_mgr.update("file.md", "name", "desc")
        await index_mgr.remove("file.md")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "file.md" not in content

    async def test_remove_nonexistent_is_noop(self, index_mgr):
        await index_mgr.update("a.md", "A", "desc a")
        await index_mgr.remove("b.md")
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "a.md" in content


class TestTruncation:
    async def test_preserves_header_on_truncation(self, tmp_path):
        index_path = tmp_path / "MEMORY.md"
        header = "# Memory Index\n\n"
        index_path.write_text(header, encoding="utf-8")
        mgr = MemoryIndexManager(index_path)
        for i in range(_MAX_LINES + 10):
            await mgr.update(f"file_{i}.md", f"name {i}", f"desc {i}")
        content = index_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        assert any(l.startswith("# Memory Index") for l in lines)


class TestAtomicWrite:
    async def test_file_exists_after_write(self, index_mgr):
        await index_mgr.update("atomic.md", "原子测试", "验证原子写入")
        assert index_mgr._path.exists()
        content = index_mgr._path.read_text(encoding="utf-8")
        assert "[原子测试](atomic.md)" in content
        assert "验证原子写入" in content

    async def test_no_temp_file_left(self, index_mgr):
        await index_mgr.update("clean.md", "清理测试", "无残留临时文件")
        parent = index_mgr._path.parent
        tmp_files = list(parent.glob(".memory_*.tmp"))
        assert tmp_files == []


class TestReconcile:
    """H-F1+F4: reconcile 启动对账自愈索引缺失/孤儿。"""

    async def test_reconcile_adds_missing_index(self, tmp_path):
        """文件存在但索引缺失 → reconcile 补齐索引行。"""
        from pathlib import Path
        index_path = Path(tmp_path) / "MEMORY.md"
        mgr = MemoryIndexManager(index_path)
        (tmp_path / "feedback_xxx.md").write_text(
            "---\nname: 用户偏好\ndescription: 偏好简洁\ntype: feedback\n---\n\nbody\n",
            encoding="utf-8",
        )
        index_path.write_text("# 记忆索引\n", encoding="utf-8")

        changed = await mgr.reconcile()
        assert changed == 1
        content = index_path.read_text(encoding="utf-8")
        assert "feedback_xxx.md" in content
        assert "用户偏好" in content

    async def test_reconcile_removes_orphan_index(self, tmp_path):
        """索引指向不存在文件 → reconcile 清理孤儿行。"""
        from pathlib import Path
        index_path = Path(tmp_path) / "MEMORY.md"
        mgr = MemoryIndexManager(index_path)
        index_path.write_text(
            "# 记忆索引\n- [Ghost](ghost.md) — 不存在的记忆\n", encoding="utf-8",
        )

        changed = await mgr.reconcile()
        assert changed == 1
        content = index_path.read_text(encoding="utf-8")
        assert "ghost.md" not in content

    async def test_reconcile_idempotent(self, tmp_path):
        """索引已一致时 reconcile 无变更（幂等）。"""
        from pathlib import Path
        index_path = Path(tmp_path) / "MEMORY.md"
        mgr = MemoryIndexManager(index_path)
        (tmp_path / "x.md").write_text(
            "---\nname: X\ndescription: desc\ntype: project\n---\n\nbody\n", encoding="utf-8",
        )
        index_path.write_text("# 索引\n- [X](x.md) — desc\n", encoding="utf-8")

        changed = await mgr.reconcile()
        assert changed == 0

    async def test_reconcile_skips_files_without_frontmatter(self, tmp_path):
        """无 frontmatter 的 .md（如 README）不被误纳入索引。"""
        from pathlib import Path
        index_path = Path(tmp_path) / "MEMORY.md"
        mgr = MemoryIndexManager(index_path)
        (tmp_path / "README.md").write_text("# Project README\n\nno frontmatter", encoding="utf-8")
        (tmp_path / "real.md").write_text(
            "---\nname: Real\ndescription: d\ntype: project\n---\n\nbody", encoding="utf-8",
        )
        index_path.write_text("# 索引\n", encoding="utf-8")

        changed = await mgr.reconcile()
        assert changed == 1  # 只索引 real.md，跳过 README.md
        content = index_path.read_text(encoding="utf-8")
        assert "real.md" in content
        assert "README.md" not in content
