"""工具降级映射 — 失败时回退到备用工具。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolDegrader:
    """工具降级映射表。应用层按需 register()。"""

    _fallbacks: dict[str, str] = field(default_factory=dict)

    def register(self, tool: str, fallback: str) -> None:
        self._fallbacks[tool] = fallback

    def get_fallback(self, tool: str) -> str | None:
        return self._fallbacks.get(tool)
