"""语义记忆写入器 — 校验、命名、文件写入、merge。"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import date
from pathlib import Path

from pydantic import BaseModel

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


def _yaml_string(s: str) -> str:
    """Quote a string for YAML frontmatter if it contains special chars."""
    if not s:
        return '""'
    needs_quoting = any(c in s for c in (
        ":", "'", '"', "#", "&", "*", "?", "|", "-", "<", ">",
        "=", "!", "%", "@", "`", ",", "{", "}", "[", "]",
    ))
    if "\n" in s or ": " in s or s.startswith("---"):
        needs_quoting = True
    if needs_quoting:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


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

    def write(self, draft: SemanticMemoryDraft, *, merged_at: date | None = None) -> Path:
        """写入 .md 文件。冲突时 merge 追加。"""
        validation = self.validate(draft)
        if not validation.passed:
            raise ValueError(validation.reason)
        slug = name_to_slug(draft.type.value, draft.name)
        file_path = self._memory_dir / f"{slug}.md"

        if file_path.exists():
            self._merge(file_path, draft, merged_at=merged_at)
        else:
            self._create(file_path, draft)

        self._index.update(f"{slug}.md", draft.name, draft.description)
        return file_path

    def write_batch(self, drafts: list[SemanticMemoryDraft]) -> WriteBatchResult:
        """批量写入，跳过校验不通过的。"""
        written: list[Path] = []
        skipped: list[tuple[SemanticMemoryDraft, str]] = []
        for draft in drafts:
            try:
                written.append(self.write(draft))
            except ValueError as e:
                skipped.append((draft, str(e)))
        return WriteBatchResult(written=written, skipped=skipped)

    def _create(self, path: Path, draft: SemanticMemoryDraft) -> None:
        frontmatter = (
            f"---\n"
            f"name: {_yaml_string(draft.name)}\n"
            f"description: {_yaml_string(draft.description)}\n"
            f"type: {draft.type.value}\n"
            f"---\n\n"
            f"{draft.body}\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter, encoding="utf-8")

    def _merge(self, path: Path, draft: SemanticMemoryDraft, *, merged_at: date | None = None) -> None:
        logger.debug("Merge 语义记忆: %s", path.name)
        effective_date = (merged_at or date.today()).isoformat()
        append_text = f"\n<!-- {effective_date} 追加 -->\n{draft.body}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(append_text)
