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
        return Settings.model_validate(final)

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

    def load_profile(self, name: str) -> dict[str, str]:
        """加载指定 profile — 占位，Phase 21-02 实现。"""
        raise NotImplementedError("load_profile 将在后续 plan 中实现")
