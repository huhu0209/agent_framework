"""Slash Commands — 命令路由器。"""

from __future__ import annotations

from agent_framework.commands.types import CommandSource, ResolvedCommand, SlashCommand
from agent_framework.skills.registry import SkillRegistry


class CommandRouter:
    """解析 /command args -> ResolvedCommand。"""

    def __init__(self, skill_registry: SkillRegistry | None = None) -> None:
        self._skill_registry = skill_registry
        self._builtins: dict[str, SlashCommand] = {}
        self._register_builtins()

    def resolve(self, user_input: str) -> ResolvedCommand:
        """解析 /command args -> ResolvedCommand。

        返回的 content 可能包含未经净化的用户输入（skill 参数），
        调用方在将 content 注入 LLM prompt 时需自行处理。
        """
        if not user_input.startswith("/"):
            return ResolvedCommand(is_command=False, content=user_input)

        stripped = user_input[1:]
        if not stripped:
            return ResolvedCommand(is_command=False, content=user_input)

        parts = stripped.split(maxsplit=1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # builtin 优先
        if name in self._builtins:
            cmd = self._builtins[name]
            if cmd.handler:
                return cmd.handler(args)
            return ResolvedCommand(is_command=True, content=f"/{name}", source=cmd.source)

        # skill
        if self._skill_registry:
            result = self._try_load_skill(self._skill_registry, name, args)
            if result.is_command:
                return result

        return ResolvedCommand(is_command=False, content=user_input)

    def _try_load_skill(self, registry: SkillRegistry, name: str, args: str) -> ResolvedCommand:
        manifest = registry.get_manifest(name)
        if manifest is None or not manifest.user_invocable:
            return ResolvedCommand(is_command=False, content=f"/{name}")

        load_result = registry.load_full_text(name)
        if load_result.is_error:
            return ResolvedCommand(is_command=False, content=f"/{name}")

        body = load_result.content.replace("$ARGUMENTS", args)

        return ResolvedCommand(
            is_command=True,
            content=body,
            source=CommandSource.SKILL,
            skill_loaded=True,
        )

    def _register_builtins(self) -> None:
        self._builtins["help"] = SlashCommand(
            name="help",
            description="显示所有可用命令",
            source=CommandSource.BUILTIN,
            handler=self._cmd_help,
        )

    def _cmd_help(self, _args: str) -> ResolvedCommand:
        lines = ["可用命令：", ""]
        for cmd in self._builtins.values():
            hint = f" {cmd.arg_hint}" if cmd.arg_hint else ""
            lines.append(f"  /{cmd.name}{hint:<20} {cmd.description}")

        if self._skill_registry:
            for name in self._skill_registry.get_names():
                manifest = self._skill_registry.get_manifest(name)
                if manifest and manifest.user_invocable:
                    lines.append(f"  /{name:<21} {manifest.description}")

        return ResolvedCommand(
            is_command=True,
            content="\n".join(lines),
            source=CommandSource.BUILTIN,
        )
