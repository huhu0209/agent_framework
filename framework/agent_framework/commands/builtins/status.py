"""Builtin command: /status"""

from __future__ import annotations

from agent_framework.commands.types import CommandSource, ResolvedCommand, SlashCommand


def register(builtins: dict[str, SlashCommand]) -> None:
    builtins["status"] = SlashCommand(
        name="status",
        description="显示 agent 状态",
        source=CommandSource.BUILTIN,
        handler=handler,
    )


def handler(_args: str) -> ResolvedCommand:
    return ResolvedCommand(
        is_command=True,
        content="agent 状态查询（未实现）",
        source=CommandSource.BUILTIN,
    )
