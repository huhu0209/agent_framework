"""Builtin command: /status"""

from __future__ import annotations

from agent_framework.commands.types import (
    CommandAction,
    CommandCategory,
    CommandResult,
    SlashCommand,
)


def register(builtins: dict[str, SlashCommand]) -> None:
    builtins["status"] = SlashCommand(
        name="status",
        description="显示 agent 状态",
        category=CommandCategory.QUERY,
        handler=_handler,
    )


def _handler(_args: str) -> CommandResult:
    return CommandResult(
        action=CommandAction.SHOW_STATUS,
        message="Agent 运行中",
    )
