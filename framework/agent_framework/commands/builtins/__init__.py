"""Builtin commands 注册入口。"""

from __future__ import annotations

from agent_framework.commands.builtins import clear, help, status
from agent_framework.commands.types import SlashCommand
from agent_framework.skills.registry import SkillRegistry


def register_all(
    builtins: dict[str, SlashCommand],
    *,
    skill_registry: SkillRegistry | None = None,
) -> None:
    help.register(builtins, skill_registry=skill_registry)
    clear.register(builtins)
    status.register(builtins)
