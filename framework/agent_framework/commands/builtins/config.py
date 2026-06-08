"""Builtin command: /config"""

from __future__ import annotations

from agent_framework.commands.types import (
    CommandAction,
    CommandCategory,
    CommandResult,
    SlashCommand,
)


def register(builtins: dict[str, SlashCommand]) -> None:
    builtins["config"] = SlashCommand(
        name="config",
        description="查看/修改运行配置",
        category=CommandCategory.CONFIG,
        arg_hint="[key] [value]",
        handler=_handler,
    )


def _handler(args: str) -> CommandResult:
    parts = args.strip().split(maxsplit=1) if args.strip() else []
    if not parts:
        return CommandResult(
            action=CommandAction.SET_CONFIG,
            message="当前配置: (default)",
        )
    if len(parts) == 1:
        return CommandResult(
            action=CommandAction.SET_CONFIG,
            message=f"{parts[0]}: (default)",
        )
    return CommandResult(
        action=CommandAction.SET_CONFIG,
        message=f"设置 {parts[0]} = {parts[1]}",
        data={parts[0]: parts[1]},
    )
