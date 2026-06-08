"""Builtin command: /clear"""

from __future__ import annotations

from agent_framework.commands.types import CommandSource, ResolvedCommand, SlashCommand


def register(builtins: dict[str, SlashCommand]) -> None:
    builtins["clear"] = SlashCommand(
        name="clear",
        description="清空聊天历史",
        source=CommandSource.BUILTIN,
        handler=handler,
    )


def handler(_args: str) -> ResolvedCommand:
    return ResolvedCommand(
        is_command=True,
        content="清空聊天历史（未实现）",
        source=CommandSource.BUILTIN,
    )
