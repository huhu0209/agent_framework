"""Hook 管理器 — 注册、匹配、执行。"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from agent_framework.config.loader import ConfigLoader
from agent_framework.hooks.types import HookConfig, HookContext, HookEvent, HookResult, HookType

logger = logging.getLogger(__name__)


def _parse_exit(code: int, stdout: str, stderr: str) -> HookResult:
    """将退出码 + stdout/stderr 转为 HookResult。"""
    if code == 0:
        updated = None
        if stdout:
            try:
                data = json.loads(stdout)
                updated = data.get("updatedInput")
            except json.JSONDecodeError:
                pass
        return HookResult(exit_code=0, stdout=stdout, updated_input=updated)

    if code == 2:
        return HookResult(exit_code=2, inject_message=stderr or stdout)

    return HookResult(exit_code=code, blocked=True, stderr=stderr or stdout)


class HookManager:
    """管理所有 Hook，按事件分组。"""

    def __init__(self, trusted: bool = False) -> None:
        self._hooks: dict[HookEvent, list[HookConfig]] = defaultdict(list)
        self._trusted = trusted
        self._session_id = str(uuid.uuid4())

    @property
    def trusted(self) -> bool:
        return self._trusted

    @classmethod
    def from_loader(
        cls, loader: ConfigLoader, trusted: bool = False
    ) -> HookManager:
        """从 ConfigLoader.discover("hooks") 路径创建 HookManager。

        discover() 返回 [global, project] 低到高优先级，
        按顺序加载 hooks.json，global 先注册，project 后追加。
        """
        manager = cls(trusted=trusted)
        for hook_dir in loader.discover("hooks"):
            hook_file = hook_dir / "hooks.json"
            if hook_file.exists():
                manager.load_from_json(hook_file)
        return manager

    def register(self, config: HookConfig) -> None:
        self._hooks[config.event].append(config)

    def load_from_json(self, path: Path) -> None:
        """从 JSON 文件批量加载 Hook 配置。跳过无效条目，不崩溃。"""
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Hook 配置文件读取失败 %s: %s", path, exc)
            return

        for event_name, entries in data.get("hooks", {}).items():
            try:
                event = HookEvent(event_name)
            except ValueError:
                logger.warning("Hook 配置跳过未知事件: %s", event_name)
                continue
            if not isinstance(entries, list):
                logger.warning("Hook 配置跳过非列表条目: %s", event_name)
                continue
            for entry in entries:
                matcher = entry.get("matcher", "*")
                for h in entry.get("hooks", []):
                    command = h.get("command", "")
                    if not command or not command.strip():
                        logger.warning("Hook 配置跳过空 command: %s/%s", event_name, matcher)
                        continue
                    self.register(HookConfig(
                        event=event,
                        matcher=matcher,
                        hook_type=HookType(h.get("type", "command")),
                        command=command,
                        timeout=h.get("timeout", 30),
                        once=h.get("once", False),
                    ))

    def _match(self, matcher: str, tool_name: str | None) -> bool:
        if matcher == "*":
            return True
        if tool_name is None:
            return False
        return fnmatch.fnmatch(tool_name, matcher)

    async def fire(self, event: HookEvent, context: HookContext) -> list[HookResult]:
        """触发事件的所有匹配 Hook。未信任工作区返回空。"""
        if not self._trusted:
            return []

        context = replace(context, session_id=self._session_id)

        results: list[HookResult] = []
        to_remove: list[HookConfig] = []
        for config in self._hooks[event]:
            if not self._match(config.matcher, context.tool_name):
                continue
            result = await self._execute_command(config, context)
            results.append(result)
            if config.once:
                to_remove.append(config)
        for config in to_remove:
            self._hooks[event].remove(config)
        return results

    async def _execute_command(
        self, config: HookConfig, context: HookContext,
    ) -> HookResult:
        """执行 shell Hook，stdin 注入 JSON context。"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", "-c", config.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdin_data: str = json.dumps({
                "session_id": context.session_id,
                "hook_event_name": context.hook_event_name,
                "tool_name": context.tool_name or "",
                "tool_input": context.tool_input or {},
                "tool_result": context.tool_result or "",
            })
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=config.timeout,
            )
            return _parse_exit(
                proc.returncode or 0,
                stdout.decode().strip(),
                stderr.decode().strip(),
            )
        except asyncio.TimeoutError:
            return HookResult(exit_code=1, blocked=True, stderr="Hook timeout")
        except OSError as exc:
            return HookResult(exit_code=1, blocked=True, stderr=f"Hook error: {exc}")
