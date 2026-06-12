"""config/ 模块叶依赖约束测试 — AST 分析验证隔离性。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


CONFIG_DIR = Path(__file__).resolve().parent.parent / "agent_framework" / "config"


class TestConfigLeafDependency:
    """config/ 模块叶依赖约束 — 不导入 agent_framework 下除 config 外的任何模块。"""

    def test_all_config_files_are_leaf_dependencies(self) -> None:
        """所有 config/*.py 文件仅导入 agent_framework.config 子模块。"""
        if not CONFIG_DIR.is_dir():
            pytest.skip("config/ 目录不存在")

        forbidden_prefixes = ("agent_framework.",)
        allowed_imports = ("agent_framework.config",)

        violations: list[str] = []
        for py_file in sorted(CONFIG_DIR.glob("*.py")):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if any(node.module.startswith(p) for p in forbidden_prefixes):
                        if not any(node.module.startswith(a) for a in allowed_imports):
                            violations.append(
                                f"{py_file.name}: imports '{node.module}'"
                            )

        assert not violations, (
            "config/ 叶依赖违规:\n" + "\n".join(violations)
        )

    def test_config_barrel_only_exports_config_symbols(self) -> None:
        """config/__init__.py 仅从 config 子模块重导出。"""
        init_file = CONFIG_DIR / "__init__.py"
        if not init_file.exists():
            pytest.skip("config/__init__.py 不存在")

        tree = ast.parse(init_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("agent_framework."):
                    assert node.module.startswith("agent_framework.config"), (
                        f"config/__init__.py imports '{node.module}' — "
                        f"must only import from agent_framework.config submodules"
                    )
