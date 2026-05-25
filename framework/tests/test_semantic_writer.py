"""语义记忆写入器测试。"""

from pathlib import Path

import pytest

from agent_framework.memory.semantic_writer import (
    SemanticWriter,
    ValidationResult,
    WriteBatchResult,
    name_to_slug,
)
from agent_framework.memory.types import MemoryType, SemanticMemoryDraft


@pytest.fixture
def writer(memory_dir):
    return SemanticWriter(memory_dir=memory_dir)


class TestNameToSlug:
    def test_ascii_name(self):
        assert name_to_slug("user", "test strategy") == "user_test_strategy"

    def test_chinese_name_hash_fallback(self):
        result = name_to_slug("feedback", "测试策略")
        assert result.startswith("feedback_")
        assert len(result) > len("feedback_")

    def test_long_name_truncated(self):
        result = name_to_slug("user", "a" * 100)
        assert len(result) <= 59

    def test_empty_name_pure_hash(self):
        result = name_to_slug("user", "")
        assert result.startswith("user_")


class TestValidation:
    def test_feedback_missing_why(self):
        draft = SemanticMemoryDraft(
            name="test", description="d", type=MemoryType.FEEDBACK,
            body="No Why here\n**How to apply:** do stuff",
        )
        result = SemanticWriter(Path(".")).validate(draft)
        assert not result.passed
        assert "Why" in result.reason

    def test_feedback_missing_how(self):
        draft = SemanticMemoryDraft(
            name="test", description="d", type=MemoryType.FEEDBACK,
            body="**Why:** reason\nNo How here",
        )
        result = SemanticWriter(Path(".")).validate(draft)
        assert not result.passed
        assert "How to apply" in result.reason

    def test_project_requires_both(self):
        draft = SemanticMemoryDraft(
            name="test", description="d", type=MemoryType.PROJECT,
            body="plain text",
        )
        result = SemanticWriter(Path(".")).validate(draft)
        assert not result.passed

    def test_user_type_no_requirement(self):
        draft = SemanticMemoryDraft(
            name="test", description="d", type=MemoryType.USER,
            body="any content",
        )
        result = SemanticWriter(Path(".")).validate(draft)
        assert result.passed

    def test_reference_type_no_requirement(self):
        draft = SemanticMemoryDraft(
            name="test", description="d", type=MemoryType.REFERENCE,
            body="any content",
        )
        result = SemanticWriter(Path(".")).validate(draft)
        assert result.passed


class TestWrite:
    def test_creates_new_file(self, writer, memory_dir):
        draft = SemanticMemoryDraft(
            name="test-strategy", description="测试描述",
            type=MemoryType.USER, body="正文内容",
        )
        path = writer.write(draft)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "---" in content
        assert "test-strategy" in content
        assert "正文内容" in content

    def test_merge_existing_file(self, writer, memory_dir):
        draft = SemanticMemoryDraft(
            name="test-strategy", description="desc",
            type=MemoryType.USER, body="first body",
        )
        writer.write(draft)
        writer.write(draft.model_copy(update={"body": "second body"}))
        content = next(memory_dir.glob("*.md")).read_text(encoding="utf-8")
        assert "first body" in content
        assert "second body" in content
        assert "追加" in content

    def test_updates_memory_index(self, writer, memory_dir):
        draft = SemanticMemoryDraft(
            name="test", description="desc",
            type=MemoryType.USER, body="body",
        )
        writer.write(draft)
        index = (memory_dir / "MEMORY.md").read_text(encoding="utf-8")
        assert "test" in index


class TestWriteBatch:
    def test_mixed_valid_invalid(self, writer):
        valid = SemanticMemoryDraft(
            name="ok", description="d", type=MemoryType.USER, body="body",
        )
        invalid = SemanticMemoryDraft(
            name="bad", description="d", type=MemoryType.FEEDBACK, body="no markers",
        )
        result = writer.write_batch([valid, invalid])
        assert len(result.written) == 1
        assert len(result.skipped) == 1
