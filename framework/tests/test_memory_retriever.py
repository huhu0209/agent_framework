"""记忆召回测试 — LLM 评分路径。"""

from pathlib import Path

import pytest

from agent_framework.memory.retriever import LLMScoringRetriever

from tests.conftest import MockAdapter


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

    async def test_scan_candidates_respects_limit(self, memory_dir: Path):
        for i in range(55):
            (memory_dir / f"file_{i}.md").write_text(
                "---\nname: test\ndescription: d\ntype: user\n---\n\nbody",
                encoding="utf-8",
            )
        adapter = MockAdapter('{"selected": []}')
        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")
        candidates = await retriever._scan_candidates(memory_dir)
        assert len(candidates) <= 50

    async def test_retrieve_warns_on_traversal(self, memory_dir: Path, caplog):
        """F1: LLM 返回越界文件名时 logger.warning 记录被拒文件名。"""
        import logging
        (memory_dir / "dummy.md").write_text("---\nname: d\ndescription: d\ntype: user\n---\n\nbody", encoding="utf-8")
        adapter = MockAdapter('{"selected": ["../../etc/passwd"]}')
        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")

        with caplog.at_level(logging.WARNING):
            result = await retriever.retrieve(query="x", memory_dir=memory_dir)

        assert result == []  # 越界被拒
        assert any("越界" in r.message or "拒绝" in r.message for r in caplog.records)

    async def test_retrieve_warns_when_all_selected_invalid(self, memory_dir: Path, caplog):
        """F1: LLM 选了文件但全部无效时汇总告警。"""
        import logging
        (memory_dir / "dummy.md").write_text("---\nname: d\ndescription: d\ntype: user\n---\n\nbody", encoding="utf-8")
        adapter = MockAdapter('{"selected": ["nonexistent.md"]}')
        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")

        with caplog.at_level(logging.WARNING):
            result = await retriever.retrieve(query="x", memory_dir=memory_dir)

        assert result == []
        assert any("全部无效" in r.message or "无效" in r.message for r in caplog.records)

    async def test_retrieve_warns_on_invalid_json(self, memory_dir: Path, caplog):
        """H-F3: LLM 返回非法 JSON 时 logger.warning，不再静默返回空。"""
        import logging
        (memory_dir / "dummy.md").write_text("---\nname: d\ndescription: d\ntype: user\n---\n\nbody", encoding="utf-8")
        adapter = MockAdapter('not valid json')
        retriever = LLMScoringRetriever(adapter=adapter, model="test-model")

        with caplog.at_level(logging.WARNING):
            result = await retriever.retrieve(query="x", memory_dir=memory_dir)

        assert result == []
        assert any("非法 JSON" in r.message for r in caplog.records)
