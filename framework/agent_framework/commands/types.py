"""Slash Commands — 类型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class CommandSource(str, Enum):
    BUILTIN = "builtin"
    SKILL = "skill"


@dataclass(frozen=True)
class ResolvedCommand:
    """resolve() 返回结果。"""

    is_command: bool
    content: str
    source: CommandSource | None = None
    skill_loaded: bool = False


@dataclass
class SlashCommand:
    """注册的 slash 命令。"""

    name: str
    description: str
    source: CommandSource
    arg_hint: str = ""
    handler: Callable[..., ResolvedCommand] | None = None
