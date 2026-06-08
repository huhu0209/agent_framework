"""Builtin command: /help"""

from __future__ import annotations

from functools import partial

from agent_framework.commands.types import (
    CommandAction,
    CommandCategory,
    CommandResult,
    SlashCommand,
)
from agent_framework.skills.registry import SkillRegistry


def register(
    builtins: dict[str, SlashCommand],
    *,
    skill_registry: SkillRegistry | None = None,
) -> None:
    builtins["help"] = SlashCommand(
        name="help",
        description="显示所有可用命令",
        category=CommandCategory.QUERY,
        handler=partial(_handler, builtins=builtins, skill_registry=skill_registry),
    )


def _handler(
    _args: str,
    *,
    builtins: dict[str, SlashCommand],
    skill_registry: SkillRegistry | None,
) -> CommandResult:
    lines = ["可用命令：", ""]
    for cmd in builtins.values():
        label = f"/{cmd.name}"
        hint = f" {cmd.arg_hint}" if cmd.arg_hint else ""
        lines.append(f"  {label + hint:<22} {cmd.description}")

    if skill_registry:
        for name in skill_registry.get_names():
            manifest = skill_registry.get_manifest(name)
            if manifest and manifest.user_invocable:
                doc = skill_registry._documents.get(name)
                if doc and not doc.active:
                    continue
                label = f"/{name}"
                lines.append(f"  {label:<22} {manifest.description}")

    return CommandResult(
        action=CommandAction.SHOW_HELP,
        message="\n".join(lines),
    )
