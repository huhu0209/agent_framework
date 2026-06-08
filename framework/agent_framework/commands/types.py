"""Commands 系统 — 类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class CommandCategory(str, Enum):
    """命令分类。"""

    SESSION = "session"
    CONFIG = "config"
    QUERY = "query"


class CommandAction(str, Enum):
    """CLI 层面要执行的动作。"""

    CLEAR_CONTEXT = "clear_context"
    COMPACT_CONTEXT = "compact_context"
    SHOW_HELP = "show_help"
    SHOW_STATUS = "show_status"
    SET_CONFIG = "set_config"
    LOAD_SKILL = "load_skill"
    NONE = "none"


@dataclass(frozen=True)
class CommandResult:
    """命令执行结果 — 结构化的 CLI 指令。"""

    action: CommandAction
    message: str = ""
    data: dict = field(default_factory=dict)
    skill_content: str = ""


@dataclass(frozen=True)
class SlashCommand:
    """注册的 slash 命令。"""

    name: str
    description: str
    category: CommandCategory
    arg_hint: str = ""
    handler: Callable[..., CommandResult] | None = field(default=None, hash=False)
