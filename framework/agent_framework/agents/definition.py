"""AgentDefinition — 从文件夹加载具名 agent(人格 + 元数据)。

一个 agent = ~/.agent-framework/agents/<名>/ 下的:
  agent.json(元数据)+ soul.md / identity.md / agents.md / tool_guidance.md(人格)。
人格复用 AgentProfile.from_directory;元数据补充 model/skills 并把 tools/permission_mode
映射到 AgentProfile 的权限字段。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from agent_framework.prompts.profiles import AgentProfile

if TYPE_CHECKING:
    from agent_framework.config.loader import ConfigLoader


@dataclass
class AgentDefinition:
    """具名 agent 的运行时定义:元数据 + 人格 profile。"""

    name: str
    description: str
    model: str | None
    skills: list[str] | None
    profile: AgentProfile

    @classmethod
    def from_directory(cls, path: Path) -> "AgentDefinition":
        """从 agent 文件夹加载。要求含 agent.json,且 name 与文件夹名一致。"""
        meta_path = path / "agent.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"agent.json 不存在: {path}")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"agent.json 解析失败: {meta_path}: {exc}") from exc

        name = meta.get("name")
        if not name:
            raise ValueError(f"agent.json 缺 name 字段: {meta_path}")
        if name != path.name:
            raise ValueError(
                f"agent.json name '{name}' 与文件夹名 '{path.name}' 不一致"
            )

        profile = AgentProfile.from_directory(path)  # 复用:读 4 个人格 md
        # 元数据映射到 profile 权限字段(不可变:model_copy)
        profile = profile.model_copy(update={
            "allowed_tools": meta.get("tools"),
            "permission_mode": meta.get("permission_mode", "ask"),
        })

        return cls(
            name=name,
            description=meta.get("description", ""),
            model=meta.get("model"),
            skills=meta.get("skills"),
            profile=profile,
        )


def discover_agent_dirs(loader: "ConfigLoader") -> list[Path]:
    """从 ConfigLoader 的 agents 目录发现含 agent.json 的子文件夹。

    返回 [global, project] 两层中所有含 agent.json 的子目录(global 在前)。
    不影响现有 AgentConfig 的 *.md 平铺发现(本函数只看子文件夹)。
    """
    result: list[Path] = []
    for base in loader.discover("agents"):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "agent.json").exists():
                result.append(child)
    return result
