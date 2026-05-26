"""Skills 系统 — 数据模型与文档解析。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_framework.memory.frontmatter import parse_frontmatter_lines

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillManifest:
    """SKILL.md frontmatter 解析结果。"""

    name: str
    description: str
    path: Path
    user_invocable: bool = True
    allowed_tools: list[str] | None = None
    model: str | None = None
    hooks: dict[str, Any] | None = None


@dataclass(frozen=True)
class SkillDocument:
    """完整 Skill 文档 = manifest + body。"""

    manifest: SkillManifest
    body: str


@dataclass(frozen=True)
class SkillLoadResult:
    """load_full_text 返回类型，显式区分成功与错误。"""

    content: str
    is_error: bool = False


def _parse_skill_document(text: str) -> tuple[dict[str, str], str]:
    """解析 SKILL.md，返回 (meta_dict, body_string)。

    无 frontmatter → ({}, text)。
    frontmatter 不闭合 → ({}, text)。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    body = "\n".join(lines[end_idx + 1 :]).strip()
    meta = parse_frontmatter_lines(lines[1:end_idx])
    return meta, body


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in ("true", "yes", "1"):
        return True
    if normalized in ("false", "no", "0"):
        return False
    return default


def _parse_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None
