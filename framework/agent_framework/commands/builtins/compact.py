"""Builtin command: /compact"""

from __future__ import annotations

from agent_framework.commands.types import (
    CommandAction,
    CommandCategory,
    CommandResult,
    SlashCommand,
)


def register(builtins: dict[str, SlashCommand]) -> None:
    builtins["compact"] = SlashCommand(
        name="compact",
        description="压缩上下文",
        category=CommandCategory.SESSION,
        handler=_handler,
    )


def _handler(_args: str) -> CommandResult:
    return CommandResult(action=CommandAction.COMPACT_CONTEXT, message="上下文已压缩")
