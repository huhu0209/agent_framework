"""Slash Commands 系统。"""

from agent_framework.commands.dispatcher import CommandDispatcher
from agent_framework.commands.types import (
    CommandAction,
    CommandCategory,
    CommandResult,
    SlashCommand,
)

__all__ = [
    "CommandDispatcher",
    "CommandAction",
    "CommandCategory",
    "CommandResult",
    "SlashCommand",
]
