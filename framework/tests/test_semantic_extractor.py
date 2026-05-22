"""SemanticExtractor 测试。"""

import json

import pytest

from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.memory.semantic_extractor import SemanticExtractor
from agent_framework.memory.types import MemoryType


class MockAdapter:
    def __init__(self, response_text: str) -> None:
        self._response = response_text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="test-id",
            model=config.model,
            content=[TextBlock(text=self._response)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=100, output_tokens=50),
        )


class TestExtractFromEvents:
    @pytest.mark.asyncio
    async def test_extracts_feedback_from_events(self):
        response = json.dumps([{
            "name": "测试策略-真实数据库",
            "description": "集成测试必须用真实数据库",
            "type": "feedback",
            "body": "测试内容\n\n**Why:** mock 失败\n**How to apply:** Docker",
        }])
        adapter = MockAdapter(response)
        extractor = SemanticExtractor(adapter=adapter, model="test-model")

        events = [("决策", "用户要求测试用真实数据库")]
        drafts = await extractor.extract_from_events(events)

        assert len(drafts) == 1
        assert drafts[0].type == MemoryType.FEEDBACK
        assert "真实数据库" in drafts[0].name

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_relevant(self):
        adapter = MockAdapter("[]")
        extractor = SemanticExtractor(adapter=adapter, model="test-model")

        events = [("进展", "完成了一些工作")]
        drafts = await extractor.extract_from_events(events)

        assert drafts == []

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self):
        adapter = MockAdapter("not json at all")
        extractor = SemanticExtractor(adapter=adapter, model="test-model")

        events = [("决策", "测试")]
        drafts = await extractor.extract_from_events(events)

        assert drafts == []


class TestExtractFromMessages:
    @pytest.mark.asyncio
    async def test_extracts_user_preference(self):
        response = json.dumps([{
            "name": "回复风格",
            "description": "用户偏好简洁回复",
            "type": "user",
            "body": "用户不希望每次回复末尾加总结。",
        }])
        adapter = MockAdapter(response)
        extractor = SemanticExtractor(adapter=adapter, model="test-model")

        drafts = await extractor.extract_from_messages("用户: 不要总结\n助手: 好的")

        assert len(drafts) == 1
        assert drafts[0].type == MemoryType.USER

    @pytest.mark.asyncio
    async def test_returns_empty_for_trivial_conversation(self):
        adapter = MockAdapter("[]")
        extractor = SemanticExtractor(adapter=adapter, model="test-model")

        drafts = await extractor.extract_from_messages("用户: 你好\n助手: 你好")

        assert drafts == []
