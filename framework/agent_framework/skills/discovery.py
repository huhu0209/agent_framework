"""Skills 系统 — 基于文件操作的动态 skill 激活。"""

from __future__ import annotations

from agent_framework.skills.registry import SkillRegistry


class SkillDiscovery:
    """监听文件操作，动态激活匹配的 paths skill。"""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def on_file_access(self, file_path: str) -> list[str]:
        """Agent 操作文件时调用，返回新激活的 skill 名称。"""
        return self._registry.activate_for_paths([file_path])
