"""记忆系统数据模型测试。"""

from datetime import datetime, timezone

from agent_framework.memory.types import (
    EpisodicRecord,
    EventType,
    MemoryLayer,
    MemorySearchConfig,
    MemorySearchResult,
)


class TestMemoryLayer:
    def test_semantic_and_episodic_values(self):
        assert MemoryLayer.SEMANTIC == "semantic"
        assert MemoryLayer.EPISODIC == "episodic"


class TestEventType:
    def test_all_event_types(self):
        assert EventType.DECISION == "决策"
        assert EventType.PREFERENCE == "偏好"
        assert EventType.ERROR == "错误"
        assert EventType.CONVENTION == "约定"
        assert EventType.PROGRESS == "进展"


class TestEpisodicRecord:
    def test_create_record(self):
        record = EpisodicRecord(
            timestamp=datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc),
            content="用户要求测试用真实数据库",
            source_file="memory/logs/2026/05/2026-05-20.md",
            line_range=(1, 5),
        )
        assert record.content == "用户要求测试用真实数据库"
        assert record.line_range == (1, 5)


class TestMemorySearchResult:
    def test_empty_result(self):
        result = MemorySearchResult(records=[], scores=[])
        assert result.records == []

    def test_with_records(self):
        record = EpisodicRecord(
            timestamp=datetime(2026, 5, 20, 14, 32, tzinfo=timezone.utc),
            content="测试内容",
            source_file="2026-05-20.md",
            line_range=(1, 3),
        )
        result = MemorySearchResult(records=[record], scores=[0.85])
        assert len(result.records) == 1
        assert result.scores[0] == 0.85


class TestMemorySearchConfig:
    def test_default_config(self):
        config = MemorySearchConfig()
        assert config.vector_weight == 0.7
        assert config.decay_half_life_days == 30
        assert config.mmr_lambda == 0.7
        assert config.top_k == 10


class TestMemoryType:
    def test_four_types(self):
        from agent_framework.memory.types import MemoryType
        assert MemoryType.USER.value == "user"
        assert MemoryType.FEEDBACK.value == "feedback"
        assert MemoryType.PROJECT.value == "project"
        assert MemoryType.REFERENCE.value == "reference"

    def test_semantic_memory_draft(self):
        from agent_framework.memory.types import SemanticMemoryDraft, MemoryType
        draft = SemanticMemoryDraft(
            name="测试策略-真实数据库",
            description="集成测试必须用真实数据库",
            type=MemoryType.FEEDBACK,
            body="集成测试必须连接真实数据库。\n\n**Why:** mock 导致生产失败\n**How to apply:** Docker 起实例",
        )
        assert draft.name == "测试策略-真实数据库"
        assert draft.type == MemoryType.FEEDBACK
