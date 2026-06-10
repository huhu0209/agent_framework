"""语义记忆写入器 — 校验、命名、文件写入、merge。"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import date
from pathlib import Path

import aiofiles
from pydantic import BaseModel

from agent_framework.memory.frontmatter import format_frontmatter
from agent_framework.memory.index_manager import MemoryIndexManager
from agent_framework.memory.types import MemoryType, SemanticMemoryDraft

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    passed: bool
    reason: str = ""


class WriteBatchResult(BaseModel):
    """批量写入结果。"""

    written: list[Path]
    skipped: list[tuple[SemanticMemoryDraft, str]]


def name_to_slug(type_value: str, name: str) -> str:
    """将 name 转为 ASCII slug，拼上类型前缀。

    非 ASCII 名称（如中文）ASCII 部分过短时追加 hash 保唯一性。
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    slug = slug[:50]

    if len(slug) < 3:
        name_hash = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug}_{name_hash}" if slug else name_hash

    return f"{type_value}_{slug}"


class SemanticWriter:
    """校验、写入语义记忆文件并维护索引。"""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir
        self._index = MemoryIndexManager(memory_dir / "MEMORY.md")

    def validate(self, draft: SemanticMemoryDraft) -> ValidationResult:
        """feedback/project 类型必须包含 Why + How to apply。"""
        if draft.type in (MemoryType.FEEDBACK, MemoryType.PROJECT):
            if "**Why:**" not in draft.body:
                return ValidationResult(
                    passed=False,
                    reason=f"{draft.type.value} 类型记忆必须包含 **Why:** 行",
                )
            if "**How to apply:**" not in draft.body:
                return ValidationResult(
                    passed=False,
                    reason=f"{draft.type.value} 类型记忆必须包含 **How to apply:** 行",
                )
        return ValidationResult(passed=True)

    async def write(self, draft: SemanticMemoryDraft, *, merged_at: date | None = None) -> Path:
        """写入 .md 文件。冲突时 merge 追加。"""
        validation = self.validate(draft)
        if not validation.passed:
            raise ValueError(validation.reason)
        slug = name_to_slug(draft.type.value, draft.name)
        file_path = self._memory_dir / f"{slug}.md"

        if file_path.exists():
            await self._merge(file_path, draft, merged_at=merged_at)
        else:
            await self._create(file_path, draft)

        await self._index.update(f"{slug}.md", draft.name, draft.description)
        return file_path

    async def write_batch(self, drafts: list[SemanticMemoryDraft]) -> WriteBatchResult:
        """批量写入，跳过校验不通过的。"""
        written: list[Path] = []
        skipped: list[tuple[SemanticMemoryDraft, str]] = []
        for draft in drafts:
            try:
                written.append(await self.write(draft))
            except ValueError as e:
                skipped.append((draft, str(e)))
        return WriteBatchResult(written=written, skipped=skipped)

    async def _create(self, path: Path, draft: SemanticMemoryDraft) -> None:
        meta = {"name": draft.name, "description": draft.description, "type": draft.type.value}
        content = f"{format_frontmatter(meta)}\n\n{draft.body}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(content)

    @staticmethod
    def _detect_overlap(existing: str, new_body: str) -> str | None:
        """检测新旧内容是否有语义重叠（基于 Why 行关键词匹配）。"""
        why_match = re.search(r"\*\*Why:\*\*\s*(.+)", new_body)
        if not why_match:
            return None
        why_phrase = why_match.group(1).strip()
        if len(why_phrase) < 4:
            return None
        # 精确匹配或子串匹配：提取新 Why 行中的关键词片段
        # 将短语按空格/标点拆分，检查连续片段是否出现在已有内容中
        tokens = re.findall(r"[\w一-鿿]{2,}", why_phrase)
        for tok in tokens:
            if tok in existing:
                return tok
        return None

    async def _merge(self, path: Path, draft: SemanticMemoryDraft, *, merged_at: date | None = None) -> None:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            existing = await f.read()
        overlap = self._detect_overlap(existing, draft.body)
        if overlap:
            logger.warning("语义记忆合并时检测到内容重叠: %s — %s", path.name, overlap)
        effective_date = (merged_at or date.today()).isoformat()
        append_text = f"\n<!-- {effective_date} 追加 -->\n{draft.body}\n"
        async with aiofiles.open(path, "a", encoding="utf-8") as f:
            await f.write(append_text)
