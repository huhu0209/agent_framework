"""记忆召回 — LLM 评分路径。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from agent_framework.memory.frontmatter import parse_frontmatter

logger = logging.getLogger(__name__)

class LLMScoringRetriever:
    """LLM 评分召回：扫描文件 → LLM 选择 → 返回内容。"""

    def __init__(self, adapter: ILLMAdapter, model: str, *, max_candidates: int = 50, max_results: int = 5) -> None:
        self._adapter = adapter
        self._model = model
        self._max_candidates = max_candidates
        self._max_results = max_results

    def _scoring_prompt(self) -> str:
        return (
            f"从以下记忆列表中选择与查询最相关的，最多 {self._max_results} 条。不确定就不包含。\n"
            '返回 JSON 格式: {"selected": ["file1.md", "file2.md"]}\n'
            "只返回 JSON，不要其他内容。"
        )

    def _scan_candidates(self, memory_dir: Path) -> list[dict[str, str]]:
        """扫描 memory 目录下的 .md 文件，提取 frontmatter 摘要。"""
        candidates = []
        for f in sorted(memory_dir.glob("*.md")):
            if len(candidates) >= self._max_candidates:
                break
            if f.name == "MEMORY.md":
                continue
            content = f.read_text(encoding="utf-8")
            meta = parse_frontmatter(content)
            candidates.append({
                "file": f.name,
                "name": meta.get("name", ""),
                "description": meta.get("description", ""),
            })

        return candidates

    async def retrieve(
        self,
        query: str,
        memory_dir: Path,
    ) -> list[dict[str, str]]:
        """LLM 选择最相关的记忆文件，返回内容。"""
        candidates = self._scan_candidates(memory_dir)
        if not candidates:
            return []

        candidate_text = "\n".join(
            f"- {c['file']}: {c['name']} — {c['description']}"
            for c in candidates
        )

        messages = [
            SystemMessage(content=self._scoring_prompt()),
            UserMessage(content=[TextBlock(
                text=f"查询: {query}\n\n可用记忆:\n{candidate_text}",
            )]),
        ]

        config = CompletionConfig(
            model=self._model,
            messages=messages,
            tools=[],
            max_tokens=256,
            temperature=0.0,
        )

        result: CompletionResult = await self._adapter.complete(config)

        selected_files = []
        for block in result.content:
            if isinstance(block, TextBlock):
                try:
                    parsed = json.loads(block.text.strip())
                    selected_files = parsed.get("selected", [])
                except json.JSONDecodeError:
                    logger.warning("LLM 评分返回非法 JSON: %s", block.text.strip()[:200])

        if not selected_files:
            return []

        selected = []
        for fname in selected_files:
            fpath = (memory_dir / fname).resolve()
            if not fpath.is_relative_to(memory_dir.resolve()):
                continue
            if fpath.exists():
                selected.append({
                    "file": fpath.name,
                    "content": fpath.read_text(encoding="utf-8"),
                })

        return selected
