"""记忆召回 — LLM 评分路径。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import aiofiles

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

    async def _scan_candidates(self, memory_dir: Path) -> list[dict[str, str]]:
        """扫描 memory 目录下的 .md 文件，提取 frontmatter 摘要。"""
        candidates = []
        for f in sorted(memory_dir.glob("*.md")):
            if len(candidates) >= self._max_candidates:
                break
            if f.name == "MEMORY.md":
                continue
            async with aiofiles.open(f, "r", encoding="utf-8") as af:
                content = await af.read()
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
        candidates = await self._scan_candidates(memory_dir)
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
                # F1: 越界文件名记录告警，不再静默跳过
                logger.warning("retriever 拒绝越界文件名: %r", fname)
                continue
            if fpath.is_file():  # F1: is_file 替代 exists，防 symlink 命中
                async with aiofiles.open(fpath, "r", encoding="utf-8") as af:
                    file_content = await af.read()
                selected.append({
                    "file": fpath.name,
                    "content": file_content,
                })
            else:
                # F1: 不存在/非文件记录告警
                logger.warning("retriever 跳过不存在/非文件: %r", fname)

        # F1: LLM 选了文件但全部无效，汇总告警（召回归零有迹可查）
        if selected_files and not selected:
            logger.warning(
                "retriever: LLM 选择了 %d 个文件但全部无效，召回为空", len(selected_files)
            )

        return selected
