"""记忆系统数据模型测试。"""

from agent_framework.memory.types import (
    EventType,
    MemoryLayer,
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
