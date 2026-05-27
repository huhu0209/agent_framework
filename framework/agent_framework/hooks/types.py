"""Hook 系统核心类型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class HookType(str, Enum):
    COMMAND = "command"


class HookEvent(str, Enum):
    SESSION_START = "SessionStart"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"


@dataclass(frozen=True)
class HookConfig:
    """单个 Hook 配置。"""
    event: HookEvent
    matcher: str
    hook_type: HookType
    command: str = ""
    timeout: int = 30
    once: bool = False


@dataclass(frozen=True)
class HookContext:
    """注入 Hook 进程的上下文。session_id 由 fire() 自动填充。"""
    hook_event_name: str = ""
    session_id: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_result: str | None = None


@dataclass(frozen=True)
class HookResult:
    """Hook 执行结果。"""
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    blocked: bool = False
    inject_message: str = ""
    updated_input: dict[str, Any] | None = None
