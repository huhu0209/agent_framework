"""语义记忆写入器 — 校验、命名、文件写入、merge。"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from agent_framework.memory.index_manager import MemoryIndexManager
from agent_framework.memory.types import MemoryType, SemanticMemoryDraft


class ValidationResult(BaseModel):
    passed: bool
    reason: str = ""


def name_to_slug(type_value: str, name: str) -> str:
    """将 name 转为 ASCII slug，拼上类型前缀。"""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    slug = slug[:50]
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

    def write(self, draft: SemanticMemoryDraft) -> Path:
        """写入 .md 文件。冲突时 merge 追加。"""
        slug = name_to_slug(draft.type.value, draft.name)
        file_path = self._memory_dir / f"{slug}.md"

        if file_path.exists():
            self._merge(file_path, draft)
        else:
            self._create(file_path, draft)

        self._index.update(f"{slug}.md", draft.name, draft.description)
        return file_path

    def write_batch(self, drafts: list[SemanticMemoryDraft]) -> list[Path]:
        """批量写入，跳过校验不通过的。"""
        results: list[Path] = []
        for draft in drafts:
            if self.validate(draft).passed:
                results.append(self.write(draft))
        return results

    def _create(self, path: Path, draft: SemanticMemoryDraft) -> None:
        frontmatter = (
            f"---\n"
            f"name: {draft.name}\n"
            f"description: {draft.description}\n"
            f"type: {draft.type.value}\n"
            f"---\n\n"
            f"{draft.body}\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter, encoding="utf-8")

    def _merge(self, path: Path, draft: SemanticMemoryDraft) -> None:
        today = date.today().isoformat()
        append_text = f"\n<!-- {today} 追加 -->\n{draft.body}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(append_text)
