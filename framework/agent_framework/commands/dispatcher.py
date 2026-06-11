"""Commands 系统 — 命令分派器。"""

from __future__ import annotations

import logging

from agent_framework.commands.builtins import register_all
from agent_framework.commands.types import (
    CommandAction,
    CommandResult,
    SlashCommand,
)
from agent_framework.config.loader import ConfigLoader
from agent_framework.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class CommandDispatcher:
    """解析 /command args -> CommandResult。"""

    def __init__(self, skill_registry: SkillRegistry | None = None) -> None:
        self._skill_registry = skill_registry
        self._builtins: dict[str, SlashCommand] = {}
        register_all(self._builtins, skill_registry=skill_registry)

    @classmethod
    def from_loader(cls, loader: ConfigLoader) -> CommandDispatcher:
        """从 ConfigLoader 创建 CommandDispatcher，自动加载 SkillRegistry。"""
        skill_registry = SkillRegistry.from_loader(loader)
        return cls(skill_registry=skill_registry)

    def resolve(self, user_input: str) -> CommandResult:
        """解析 /command args -> CommandResult。

        返回的 message/skill_content 可能包含未经净化的用户输入
        （skill 参数），调用方在注入 LLM prompt 时需自行处理。

        不限制输入长度，调用方可按需截断。
        """
        if not user_input.startswith("/"):
            return CommandResult(action=CommandAction.NONE, message=user_input)

        stripped = user_input[1:]
        if not stripped:
            return CommandResult(action=CommandAction.NONE, message=user_input)

        parts = stripped.split(maxsplit=1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # builtin 优先
        if name in self._builtins:
            cmd = self._builtins[name]
            if cmd.handler:
                return cmd.handler(args)
            return CommandResult(
                action=CommandAction.NONE,
                message=f"/{name}",
            )

        # skill fallback
        if self._skill_registry:
            result = self._try_load_skill(self._skill_registry, name, args)
            if result.action != CommandAction.NONE:
                return result

        return CommandResult(action=CommandAction.NONE, message=user_input)

    def _try_load_skill(self, registry: SkillRegistry, name: str, args: str) -> CommandResult:
        """加载 skill 并替换参数占位符。

        使用 str.replace() 替换正文中所有出现的 ``$ARGUMENTS``。
        skill 正文应只包含一个 ``$ARGUMENTS`` 占位符。
        """
        manifest = registry.get_manifest(name)
        if manifest is None or not manifest.user_invocable:
            return CommandResult(action=CommandAction.NONE, message=f"/{name}")

        load_result = registry.load_full_text(name)
        if load_result.is_error:
            logger.debug("Skill '%s' 加载失败: %s", name, load_result.content)
            return CommandResult(action=CommandAction.NONE, message=f"/{name}")

        body = load_result.content.replace("$ARGUMENTS", args)
        return CommandResult(
            action=CommandAction.LOAD_SKILL,
            message=f"Skill '{name}' loaded",
            skill_content=body,
        )
