"""记忆召回测试 — LLM 评分路径。"""

from pathlib import Path

import pytest

from agent_framework.llm.types import CompletionConfig, CompletionResult, StopReason, TextBlock, UsageStats
from agent_framework.memory.retriever import LLMScoringRetriever


class MockAdapter:
    def __init__(self, response_text: str) -> None:
        self._response = response_text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            content=[TextBlock(text=self._response)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=100, output_tokens=50),
            id="test-id",
            model=config.model,
        )


@pytest.fixture
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


class TestLLMScoringRetriever:
    async def test_retrieve_selects_relevant(self, memory_dir: Path):
        adapter = MockAdapter('{"selected": ["feedback_testing.md"]}')

        memory_file = memory_dir / "feedback_testing.md"
        memory_file.write_text(
            "---\nname: 测试策略\ndescription: 测试用真实数据库\ntype: feedback\n---\n\n测试内容",
            encoding="utf-8",
        )

        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")
        result = await retriever.retrieve(
            query="怎么跑测试",
            memory_dir=memory_dir,
        )

        assert len(result) >= 1
        assert result[0]["file"] == "feedback_testing.md"
        assert "测试内容" in result[0]["content"]

    async def test_retrieve_empty_dir(self, memory_dir: Path):
        adapter = MockAdapter('{"selected": []}')

        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")
        result = await retriever.retrieve(
            query="随便查",
            memory_dir=memory_dir,
        )

        assert result == []

    async def test_retrieve_skips_memory_index(self, memory_dir: Path):
        adapter = MockAdapter('{"selected": []}')

        (memory_dir / "MEMORY.md").write_text("- [test](test.md)", encoding="utf-8")

        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")
        result = await retriever.retrieve(query="test", memory_dir=memory_dir)
        assert result == []

    async def test_retrieve_skips_path_traversal(self, memory_dir: Path):
        adapter = MockAdapter('{"selected": ["../../etc/passwd", "feedback_testing.md"]}')
        memory_file = memory_dir / "feedback_testing.md"
        memory_file.write_text(
            "---\nname: test\ndescription: d\ntype: user\n---\n\ncontent",
            encoding="utf-8",
        )

        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")
        result = await retriever.retrieve(query="test", memory_dir=memory_dir)

        files = [r["file"] for r in result]
        assert all("../../" not in f for f in files)
        assert "feedback_testing.md" in files

    def test_scan_candidates_respects_limit(self, memory_dir: Path):
        for i in range(55):
            (memory_dir / f"file_{i}.md").write_text(
                "---\nname: test\ndescription: d\ntype: user\n---\n\nbody",
                encoding="utf-8",
            )
        adapter = MockAdapter('{"selected": []}')
        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")
        candidates = retriever._scan_candidates(memory_dir)
        assert len(candidates) <= 50
