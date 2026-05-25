"""SemanticWriter 测试。"""

from pathlib import Path

import pytest

from agent_framework.memory.types import MemoryType, SemanticMemoryDraft
from agent_framework.memory.semantic_writer import SemanticWriter, WriteBatchResult, name_to_slug, ValidationResult, _yaml_string


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


def _feedback_draft(**overrides) -> SemanticMemoryDraft:
    defaults = dict(
        name="测试策略-真实数据库",
        description="集成测试必须用真实数据库",
        type=MemoryType.FEEDBACK,
        body="测试内容\n\n**Why:** mock 失败\n**How to apply:** Docker",
    )
    defaults.update(overrides)
    return SemanticMemoryDraft(**defaults)


def _user_draft(**overrides) -> SemanticMemoryDraft:
    defaults = dict(
        name="回复风格",
        description="用户喜欢简洁回复",
        type=MemoryType.USER,
        body="用户不希望在回复末尾加总结。",
    )
    defaults.update(overrides)
    return SemanticMemoryDraft(**defaults)


class TestNameToSlug:
    def test_basic(self):
        result = name_to_slug("feedback", "测试策略-真实数据库")
        assert result.startswith("feedback_")
        assert len(result) > len("feedback_")  # hash suffix appended

    def test_chinese_name(self):
        result = name_to_slug("user", "回复风格")
        assert result.startswith("user_")
        assert len(result) > len("user_")  # hash suffix appended

    def test_special_chars_removed(self):
        result = name_to_slug("project", "v3.2 迁移计划!!")
        assert ".." not in result
        assert "!!" not in result

    def test_truncation(self):
        long_name = "a" * 100
        result = name_to_slug("feedback", long_name)
        assert len(result) <= 60 + len("feedback_")

    def test_pure_ascii_no_hash(self):
        result = name_to_slug("feedback", "testing strategy")
        assert result == "feedback_testing_strategy"
        assert len(result) == len("feedback_testing_strategy")

    def test_hash_uniqueness(self):
        a = name_to_slug("user", "测试策略")
        b = name_to_slug("user", "测试方案")
        assert a != b  # different Chinese names produce different hashes


class TestValidation:
    def test_feedback_with_why_and_how_passes(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        result = writer.validate(_feedback_draft())
        assert result.passed

    def test_feedback_missing_why_fails(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        draft = _feedback_draft(body="no why or how")
        result = writer.validate(draft)
        assert not result.passed
        assert "Why" in result.reason

    def test_feedback_missing_how_to_apply_fails(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        draft = _feedback_draft(body="some text\n**Why:** reason\nbut no how")
        result = writer.validate(draft)
        assert not result.passed
        assert "How to apply" in result.reason

    def test_user_type_no_structure_required(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        result = writer.validate(_user_draft())
        assert result.passed

    def test_project_requires_structure(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        draft = SemanticMemoryDraft(
            name="合并冻结",
            description="冻结非关键合并",
            type=MemoryType.PROJECT,
            body="no structure",
        )
        result = writer.validate(draft)
        assert not result.passed


class TestWrite:
    def test_create_new_file(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        path = writer.write(_feedback_draft())

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "name:" in content
        assert "**Why:**" in content

    def test_merge_appends_to_existing(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        writer.write(_feedback_draft())

        updated = _feedback_draft(body="追加内容\n\n**Why:** 新原因\n**How to apply:** 新方法")
        writer.write(updated)

        content = (memory_dir / "MEMORY.md").read_text(encoding="utf-8")
        lines = [l for l in content.strip().split("\n") if l.strip()]
        assert len(lines) == 1

    def test_write_batch_skips_invalid(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        drafts = [
            _feedback_draft(),  # valid
            _feedback_draft(body="invalid"),  # invalid: no Why/How
            _user_draft(),  # valid
        ]
        result = writer.write_batch(drafts)
        assert len(result.written) == 2
        assert len(result.skipped) == 1
        assert "Why" in result.skipped[0][1]

    def test_creates_memory_md_index(self, memory_dir: Path):
        writer = SemanticWriter(memory_dir)
        writer.write(_feedback_draft())

        index_path = memory_dir / "MEMORY.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "测试策略-真实数据库" in content


class TestYamlString:
    def test_plain_text(self):
        assert _yaml_string("hello") == "hello"

    def test_contains_colon_space(self):
        result = _yaml_string("key: value")
        assert result.startswith('"')
        assert result.endswith('"')

    def test_contains_quotes(self):
        result = _yaml_string("it's a \"test\"")
        assert '\\"' in result

    def test_empty_string(self):
        assert _yaml_string("") == '""'
