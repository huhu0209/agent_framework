"""AgentProfile — Agent 的完整灵魂定义。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class PromptBlock(BaseModel):
    """system prompt 的一个组成块。"""

    name: str
    content: str
    source: Literal["file", "auto_generated", "injected"]
    stability: Literal["static", "semi_static", "dynamic"]
    cache_breakpoint: bool


class AgentProfile(BaseModel):
    """定义一个 Agent 的完整灵魂。"""

    name: str
    description: str

    soul: str = ""
    agents_rules: str = ""
    identity: str = ""
    user_context: str | None = None

    tool_guidance: str | None = None

    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    permission_mode: Literal["accept", "ask", "deny"] = "ask"

    @classmethod
    def from_directory(cls, path: Path) -> AgentProfile:
        """从目录加载 profile。目录名作为 name，子文件作为各模块。"""
        name = path.name
        soul = _read_file(path / "soul.md")
        agents_rules = _read_file(path / "agents.md")
        identity = _read_file(path / "identity.md")
        tool_guidance_raw = _read_file(path / "tool_guidance.md")

        return cls(
            name=name,
            description=f"从 {path} 加载的 profile",
            soul=soul,
            agents_rules=agents_rules,
            identity=identity,
            tool_guidance=tool_guidance_raw or None,
        )


def _read_file(path: Path) -> str:
    """读文件内容，不存在返回空字符串。"""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
