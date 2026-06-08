"""Skills 系统 — 类型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class SkillSource(str, Enum):
    """Skill 来源，决定安全边界。"""

    USER = "user"
    PROJECT = "project"
    BUNDLED = "bundled"
    MCP = "mcp"


@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    path: Path
    source: SkillSource
    user_invocable: bool = True
    allowed_tools: list[str] | None = None
    model: str | None = None
    disable_model_invocation: bool = False
    context: str | None = None
    paths: list[str] | None = None
    hooks: dict[str, Any] | None = None


@dataclass(frozen=True)
class SkillDocument:
    manifest: SkillManifest
    body: str
    active: bool = True


@dataclass(frozen=True)
class SkillLoadResult:
    content: str
    is_error: bool = False
