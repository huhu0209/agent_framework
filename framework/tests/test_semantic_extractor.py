"""语义记忆提取器测试。"""

import pytest

from agent_framework.memory.semantic_extractor import SemanticExtractor
from agent_framework.memory.types import SemanticMemoryDraft
from tests.conftest import MockAdapter


class TestExtractFromEvents:
    async def test_extracts_multiple_drafts(self):
        response = '[{"name": "策略", "description": "测试用真实DB", "type": "feedback", "body": "**Why:** mock 失败\\n**How to apply:** Docker"}]'
        ext = SemanticExtractor(adapter=MockAdapter(response), model="test")
        result = await ext.extract_from_events([("决策", "用真实数据库")])
        assert len(result) == 1
        assert result[0].name == "策略"

    async def test_empty_array(self):
        ext = SemanticExtractor(adapter=MockAdapter("[]"), model="test")
        result = await ext.extract_from_events([("决策", "test")])
        assert result == []


class TestExtractFromMessages:
    async def test_extracts_from_conversation(self):
        response = '[{"name": "偏好", "description": "偏好详细解释", "type": "user", "body": "用户喜欢详细解释"}]'
        ext = SemanticExtractor(adapter=MockAdapter(response), model="test")
        result = await ext.extract_from_messages("用户: 请详细解释")
        assert len(result) == 1
        assert result[0].type.value == "user"


class TestEdgeCases:
    async def test_invalid_json_returns_empty(self):
        ext = SemanticExtractor(adapter=MockAdapter("not json"), model="test")
        result = await ext.extract_from_events([("决策", "test")])
        assert result == []

    async def test_missing_field_skips_item(self):
        response = '[{"name": "test"}]'
        ext = SemanticExtractor(adapter=MockAdapter(response), model="test")
        result = await ext.extract_from_events([("决策", "test")])
        assert result == []

    async def test_invalid_type_skips_item(self):
        response = '[{"name": "t", "description": "d", "type": "invalid", "body": "b"}]'
        ext = SemanticExtractor(adapter=MockAdapter(response), model="test")
        result = await ext.extract_from_events([("决策", "test")])
        assert result == []

    async def test_non_list_returns_empty(self):
        ext = SemanticExtractor(adapter=MockAdapter("{}"), model="test")
        result = await ext.extract_from_events([("决策", "test")])
        assert result == []

    async def test_empty_textblock_returns_empty(self):
        ext = SemanticExtractor(adapter=MockAdapter(""), model="test")
        result = await ext.extract_from_events([("决策", "test")])
        assert result == []
