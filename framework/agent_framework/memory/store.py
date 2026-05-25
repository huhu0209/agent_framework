"""记忆系统门面 — 统一搜索情景和语义两层。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from agent_framework.llm.base import ILLMAdapter
from agent_framework.memory.log_manager import EpisodicLogManager
from agent_framework.memory.retriever import LLMScoringRetriever
from agent_framework.memory.semantic_writer import SemanticWriter
from agent_framework.memory.types import SemanticMemoryDraft

logger = logging.getLogger(__name__)


@dataclass
class MemorySearchResult:
    """统一搜索结果。"""

    source: str          # "episodic" | "semantic"
    file: str
    content: str
    relevance: float | None = None


class MemoryStore:
    """记忆系统门面 — 统一搜索情景和语义两层。"""

    def __init__(
        self,
        adapter: ILLMAdapter,
        model: str,
        memory_dir: Path,
        *,
        max_candidates: int = 50,
        max_results: int = 5,
    ) -> None:
        self._memory_dir = memory_dir
        self._log_manager = EpisodicLogManager(memory_dir=memory_dir)
        self._retriever = LLMScoringRetriever(adapter=adapter, model=model)
        self._writer = SemanticWriter(memory_dir=memory_dir)

    async def search(
        self, query: str, *, top_k: int = 10,
    ) -> list[MemorySearchResult]:
        """统一搜索：先情景（关键词），再语义（LLM 评分），合并返回。"""
        results: list[MemorySearchResult] = []

        # 情景层：关键词搜索
        episodic = self._search_episodic(query, top_k=top_k)
        results.extend(episodic)

        # 语义层：LLM 评分召回
        semantic = await self._search_semantic(query)
        # 去重：语义结果不与情景重复
        seen_files = {r.file for r in results}
        for r in semantic:
            if r.file not in seen_files:
                results.append(r)
                seen_files.add(r.file)

        return results

    async def write(self, draft: SemanticMemoryDraft) -> Path:
        """语义记忆写入，委托给 SemanticWriter。"""
        return self._writer.write(draft)

    def _search_episodic(
        self, query: str, *, top_k: int = 10,
    ) -> list[MemorySearchResult]:
        """情景记忆关键词搜索。"""
        dates = self._log_manager.list_dates()
        results: list[MemorySearchResult] = []
        query_lower = query.lower()

        for date in reversed(dates):
            content = self._log_manager.read_log(date)
            if content is None:
                continue
            blocks = re.split(r"(?=^## )", content, flags=re.MULTILINE)
            for block in blocks:
                if not block.strip():
                    continue
                if query_lower in block.lower():
                    results.append(MemorySearchResult(
                        source="episodic",
                        file=f"{date}.md",
                        content=block.strip(),
                    ))
                    if len(results) >= top_k:
                        return results

        return results

    async def _search_semantic(
        self, query: str,
    ) -> list[MemorySearchResult]:
        """语义记忆 LLM 评分召回。"""
        raw = await self._retriever.retrieve(query, self._memory_dir)
        return [
            MemorySearchResult(
                source="semantic",
                file=item["file"],
                content=item["content"],
            )
            for item in raw
        ]
