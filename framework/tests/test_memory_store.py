"""MemoryStore 统一搜索门面测试。"""

import json
from datetime import datetime, timezone

import pytest

from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.semantic_writer import SemanticWriter
from agent_framework.memory.store import MemorySearchResult, MemoryStore
from agent_framework.memory.types import EventType, MemoryType, SemanticMemoryDraft
from tests.conftest import MockAdapter


@pytest.fixture
def memory_store(memory_dir):
    adapter = MockAdapter('{"selected": []}')
    return MemoryStore(adapter=adapter, model="test-model", memory_dir=memory_dir)


class TestSearch:
    async def test_episodic_search_finds_match(self, memory_store, memory_dir):
        """情景层关键词匹配。"""
        log_mgr = EpisodicLogManager(memory_dir=memory_dir)
        ts = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)
        log_mgr.append(ts, EventType.DECISION, "选择 FastAPI 框架")

        results = await memory_store.search("FastAPI")
        assert len(results) >= 1
        assert results[0].source == "episodic"

    async def test_empty_dir_returns_empty(self, memory_store):
        results = await memory_store.search("anything")
        assert results == []

    async def test_semantic_search_finds_match(self, memory_dir):
        """语义层 LLM 评分召回。"""
        # 先写入语义记忆
        writer = SemanticWriter(memory_dir=memory_dir)
        path = writer.write(SemanticMemoryDraft(
            name="后端框架", description="使用 FastAPI",
            type=MemoryType.PROJECT,
            body="**Why:** 性能好\n**How to apply:** 新接口用 FastAPI",
        ))

        # retriever 会选中该文件 — 用实际生成的文件名
        response = json.dumps({"selected": [path.name]})
        adapter = MockAdapter(response)
        store = MemoryStore(adapter=adapter, model="test-model", memory_dir=memory_dir)

        results = await store.search("后端")
        assert len(results) >= 1
        semantic_results = [r for r in results if r.source == "semantic"]
        assert len(semantic_results) >= 1


class TestMemorySearchResult:
    def test_creation(self):
        result = MemorySearchResult(
            source="episodic", file="2026-05-20.md",
            content="test content", relevance=None,
        )
        assert result.source == "episodic"
        assert result.content == "test content"

    def test_with_relevance(self):
        result = MemorySearchResult(
            source="semantic", file="test.md",
            content="content", relevance=0.95,
        )
        assert result.relevance == 0.95
