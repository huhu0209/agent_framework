"""AgentDefinition — 从文件夹加载具名 agent(人格 + 元数据)。

一个 agent = ~/.agent-framework/agents/<名>/ 下的:
  agent.json(元数据)+ soul.md / identity.md / agents.md / tool_guidance.md(人格)。
人格复用 AgentProfile.from_directory;元数据补充 model/skills 并把 tools/permission_mode
映射到 AgentProfile 的权限字段。
"""
from __future__ import annotations

import json
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from agent_framework.prompts.profiles import AgentProfile

if TYPE_CHECKING:
    from agent_framework.config.loader import ConfigLoader

# AgentProfile.permission_mode 的合法值(model_copy 不校验,故在此显式约束)。
# L-2: 从 AgentProfile.permission_mode 的 Literal 派生,单一来源防两处定义漂移。
_VALID_PERMISSION_MODES = set(
    typing.get_args(AgentProfile.model_fields["permission_mode"].annotation)
)


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

        # HIGH-2: symlink 防护 — agent 目录内的 json/md 不得是 symlink 或经 ../ 逃逸,
        # 防 soul.md -> /etc/passwd 被全文读入 system prompt(复用 skills G3 模式)。
        resolved_root = path.resolve()
        for fname in ("agent.json", "soul.md", "identity.md", "agents.md", "tool_guidance.md"):
            f = path / fname
            if not f.exists():
                continue
            try:
                if f.is_symlink() or not f.resolve().is_relative_to(resolved_root):
                    raise ValueError(f"{fname} 是 symlink 或逃逸 agent 目录,拒绝加载: {f}")
            except OSError as exc:
                raise ValueError(f"无法解析 {fname}: {f}") from exc

        profile = AgentProfile.from_directory(path)  # 复用:读 4 个人格 md
        # 元数据映射到 profile 权限字段(不可变:model_copy)。model_copy 默认不触发 pydantic 校验,
        # 故先显式校验类型:M2 review(permission_mode); CRITICAL-1 review(tools 若为字符串,
        # PermissionPipeline.check 的 `tool in allowed_tools` 会退化为子串匹配,'e' in 'read'=True)。
        permission_mode = meta.get("permission_mode", "ask")
        if permission_mode not in _VALID_PERMISSION_MODES:
            raise ValueError(
                f"非法 permission_mode: {permission_mode!r},合法值: {sorted(_VALID_PERMISSION_MODES)}"
            )
        tools = meta.get("tools")
        if tools is not None and (not isinstance(tools, list) or not all(isinstance(t, str) for t in tools)):
            raise ValueError(f"非法 tools: {tools!r},应为 list[str]")
        skills = meta.get("skills")
        if skills is not None and (not isinstance(skills, list) or not all(isinstance(s, str) for s in skills)):
            raise ValueError(f"非法 skills: {skills!r},应为 list[str]")
        model = meta.get("model")
        if model is not None and not isinstance(model, str):
            raise ValueError(f"非法 model: {model!r},应为 str")
        profile = profile.model_copy(update={
            "allowed_tools": tools,
            "permission_mode": permission_mode,
        })

        return cls(
            name=name,
            description=meta.get("description", ""),
            model=model,
            skills=skills,
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
