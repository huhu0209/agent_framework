"""配置加载 — ConfigLoader 统一入口。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_framework.config.merge import merge_settings
from agent_framework.config.settings import Settings, apply_env_vars

# 8 种模块类型 -> 子目录名映射
MODULE_DIRS: dict[str, str] = {
    "skills": "skills",
    "agents": "agents",
    "commands": "commands",
    "hooks": "hooks",
    "rules": "rules",
    "profiles": "profiles",
    "memory": "memory",
    "mcp": "mcp",
}


def _read_text_file(path: Path) -> str:
    """读取文件内容，不存在返回空字符串。"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _find_git_root(start: Path) -> Path | None:
    """从 start 向上查找包含 .git/ 的目录。"""
    if (start / ".git").is_dir():
        return start
    for parent in start.parents:
        if (parent / ".git").is_dir():
            return parent
    return None


# Profile 子文件名列表
PROFILE_FILES: list[str] = ["soul.md", "agents.md", "identity.md", "tool_guidance.md"]


def _validate_profile_name(name: str) -> None:
    """验证 profile 名称不含路径遍历字符。"""
    if not name or "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"无效的 profile 名称: {name}")


class ConfigLoader:
    """配置加载统一入口。

    提供 load_settings() 四级覆盖链和 discover() 模块路径发现。
    """

    def __init__(
        self,
        global_dir: Path = Path.home(),
        project_dir: Path = Path.cwd(),
    ) -> None:
        self._global_dir = global_dir / ".agent-framework"
        self._project_dir = project_dir / ".agent-framework"

    def _read_json(self, path: Path) -> dict[str, Any]:
        """读取 JSON 文件，不存在返回空 dict。

        JSONDecodeError 时 raise ValueError 提示具体文件路径。
        """
        if not path.exists():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"配置文件格式错误: {path}"
            ) from exc
        except OSError as exc:
            raise ValueError(
                f"配置文件读取失败: {path}"
            ) from exc

    def load_settings(self) -> Settings:
        """四级覆盖链加载 settings.json，返回 Settings 实例。

        优先级: env > local > project > global
        无缓存，每次调用重新加载。
        """
        global_cfg = self._read_json(self._global_dir / "settings.json")
        project_cfg = self._read_json(self._project_dir / "settings.json")
        local_cfg = self._read_json(self._project_dir / "settings.local.json")
        merged = merge_settings(global_cfg, project_cfg, local_cfg)
        final = apply_env_vars(merged, dict(os.environ))
        try:
            return Settings.model_validate(final)
        except Exception as exc:
            raise ValueError(
                f"配置验证失败: {exc}"
            ) from exc

    def discover(self, module_name: str) -> list[Path]:
        """返回优先级从低到高的模块目录路径列表。

        Args:
            module_name: 模块类型名，必须在 MODULE_DIRS 中。

        Returns:
            存在的目录路径列表，按 [global, project] 顺序排列。

        Raises:
            ValueError: 未知模块类型。
        """
        sub_dir = MODULE_DIRS.get(module_name)
        if sub_dir is None:
            raise ValueError(f"未知模块类型: {module_name}")
        paths: list[Path] = []
        for base in (self._global_dir, self._project_dir):
            module_path = base / sub_dir
            if module_path.is_dir():
                paths.append(module_path)
        return paths

    def _parent_agents_chain(self) -> list[tuple[Path, str]]:
        """收集从 .git 根到 project_root 的父目录链中 AGENTS.md 路径。

        低优先级在前（靠近 .git 根），高优先级在后（靠近 project_root）。
        """
        project_root = self._project_dir.parent
        git_root = _find_git_root(project_root)
        if git_root is None or git_root == project_root:
            return []

        # 从 project_root 向上收集到 git_root 的中间目录
        chain_dirs: list[Path] = []
        current = project_root
        while current != git_root and current != current.parent:
            chain_dirs.append(current)
            current = current.parent

        # 反转: 从 git_root 附近到 project_root 附近（低到高优先级）
        result: list[tuple[Path, str]] = []
        for d in reversed(chain_dirs):
            try:
                label = str(d.relative_to(project_root)) + "/AGENTS.md"
            except ValueError:
                label = str(d) + "/AGENTS.md"
            result.append((d / "AGENTS.md", label))
        return result

    def load_agents_md(self) -> str:
        """拼接完整的 AGENTS.md 指令链。

        顺序: global -> project -> local -> 父目录链 -> user.md
        每个片段带 '# Source: <label>' 标题，片段间双换行分隔。
        文件缺失或空内容静默跳过。
        """
        sources: list[tuple[Path, str]] = [
            (self._global_dir / "AGENTS.md", "~/.agent-framework/AGENTS.md"),
            (self._project_dir / "AGENTS.md", ".agent-framework/AGENTS.md"),
            (self._project_dir / "AGENTS.local.md", ".agent-framework/AGENTS.local.md"),
        ]
        sources.extend(self._parent_agents_chain())
        sources.append(
            (self._global_dir / "user.md", "~/.agent-framework/user.md")
        )

        parts: list[str] = []
        for path, label in sources:
            content = _read_text_file(path)
            if content.strip():
                parts.append(f"# Source: {label}\n{content}")

        return "\n\n".join(parts)

    def load_profile(self, name: str) -> dict[str, str]:
        """加载并合并指定 profile 的字段。

        先加载 global profiles/<name>/ 的子文件，再用 project
        profiles/<name>/ 的非空子文件覆盖。缺失子文件静默跳过。

        Args:
            name: profile 目录名（如 "default"）。

        Returns:
            {field_name: content}，field_name 去掉 .md 后缀。
        """
        result: dict[str, str] = {}
        _validate_profile_name(name)

        # 先加载 global
        global_profile_dir = self._global_dir / "profiles" / name
        for filename in PROFILE_FILES:
            field = filename.removesuffix(".md")
            content = _read_text_file(global_profile_dir / filename).strip()
            if content:
                result[field] = content

        # 再用 project 的非空字段覆盖
        project_profile_dir = self._project_dir / "profiles" / name
        for filename in PROFILE_FILES:
            field = filename.removesuffix(".md")
            content = _read_text_file(project_profile_dir / filename).strip()
            if content:
                result[field] = content

        return result
