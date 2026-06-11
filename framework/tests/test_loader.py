"""ConfigLoader + discover + load_settings 测试。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_framework.config.loader import MODULE_DIRS, ConfigLoader


class TestConfigLoaderConstruction:
    """ConfigLoader 构造函数测试。"""

    def test_default_global_dir(self, tmp_path: Path) -> None:
        """默认 global_dir=Path.home()，内部 _global_dir 自动拼接 /.agent-framework/。"""
        loader = ConfigLoader()
        assert loader._global_dir == Path.home() / ".agent-framework"

    def test_default_project_dir(self, tmp_path: Path) -> None:
        """默认 project_dir=Path.cwd()，内部 _project_dir 自动拼接 /.agent-framework/。"""
        loader = ConfigLoader()
        assert loader._project_dir == Path.cwd() / ".agent-framework"

    def test_custom_paths(self, tmp_path: Path) -> None:
        """传入 tmp_path 参数，_global_dir 和 _project_dir 拼接 /.agent-framework/。"""
        global_base = tmp_path / "global"
        project_base = tmp_path / "project"
        global_base.mkdir()
        project_base.mkdir()
        loader = ConfigLoader(global_dir=global_base, project_dir=project_base)
        assert loader._global_dir == global_base / ".agent-framework"
        assert loader._project_dir == project_base / ".agent-framework"


class TestLoadSettings:
    """load_settings() 四级覆盖链测试。"""

    def _make_loader(self, tmp_path: Path) -> ConfigLoader:
        """创建使用 tmp_path 的 ConfigLoader。"""
        global_base = tmp_path / "global"
        project_base = tmp_path / "project"
        global_base.mkdir()
        project_base.mkdir()
        return ConfigLoader(global_dir=global_base, project_dir=project_base)

    def test_no_config_files_returns_defaults(self, tmp_path: Path) -> None:
        """无配置文件 — 返回全默认 Settings 实例。"""
        loader = self._make_loader(tmp_path)
        settings = loader.load_settings()
        assert settings.model == "claude-sonnet-4-20250514"
        assert settings.llm.provider == "anthropic"
        assert settings.server.port == 30002

    def test_global_settings_override(self, tmp_path: Path) -> None:
        """global settings.json 存在时，对应字段覆盖默认值。"""
        loader = self._make_loader(tmp_path)
        global_cfg = tmp_path / "global" / ".agent-framework"
        global_cfg.mkdir()
        (global_cfg / "settings.json").write_text(
            json.dumps({"model": "gpt-4"}), encoding="utf-8"
        )
        settings = loader.load_settings()
        assert settings.model == "gpt-4"

    def test_four_level_override_chain(self, tmp_path: Path) -> None:
        """四级覆盖链 — env > local > project > global，验证标量取最高优先级。"""
        loader = self._make_loader(tmp_path)

        # 创建所有配置目录
        global_cfg = tmp_path / "global" / ".agent-framework"
        project_cfg = tmp_path / "project" / ".agent-framework"
        global_cfg.mkdir(parents=True, exist_ok=True)
        project_cfg.mkdir(parents=True, exist_ok=True)

        # global: model=a, permissions.allow=["Read"]
        (global_cfg / "settings.json").write_text(
            json.dumps({"model": "a", "permissions": {"allow": ["Read(*)"]}}),
            encoding="utf-8",
        )
        # project: model=b, permissions.allow=["Write"]
        (project_cfg / "settings.json").write_text(
            json.dumps({"model": "b", "permissions": {"allow": ["Write(*)"]}}),
            encoding="utf-8",
        )
        # local: model=c
        (project_cfg / "settings.local.json").write_text(
            json.dumps({"model": "c"}), encoding="utf-8"
        )

        settings = loader.load_settings()
        # 标量: local 覆盖 project 覆盖 global
        assert settings.model == "c"
        # list: 并集 ["Read(*)", "Write(*)"]
        assert "Read(*)" in settings.permissions.allow
        assert "Write(*)" in settings.permissions.allow

    def test_env_var_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """设置 APP_MODEL 环境变量，最终 Settings.model 等于环境变量值。"""
        loader = self._make_loader(tmp_path)

        project_cfg = tmp_path / "project" / ".agent-framework"
        project_cfg.mkdir(parents=True, exist_ok=True)
        (project_cfg / "settings.json").write_text(
            json.dumps({"model": "from-file"}), encoding="utf-8"
        )

        monkeypatch.setenv("APP_MODEL", "from-env")
        settings = loader.load_settings()
        assert settings.model == "from-env"

    def test_json_format_error_raises_value_error(self, tmp_path: Path) -> None:
        """JSON 格式错误 — raise ValueError，异常信息包含文件路径。"""
        loader = self._make_loader(tmp_path)

        global_cfg = tmp_path / "global" / ".agent-framework"
        global_cfg.mkdir(parents=True, exist_ok=True)
        (global_cfg / "settings.json").write_text("{invalid json", encoding="utf-8")

        with pytest.raises(ValueError, match="配置文件格式错误"):
            loader.load_settings()


class TestDiscover:
    """discover() 模块路径发现测试。"""

    def _make_loader(self, tmp_path: Path) -> ConfigLoader:
        """创建使用 tmp_path 的 ConfigLoader。"""
        global_base = tmp_path / "global"
        project_base = tmp_path / "project"
        global_base.mkdir()
        project_base.mkdir()
        return ConfigLoader(global_dir=global_base, project_dir=project_base)

    def test_both_exist(self, tmp_path: Path) -> None:
        """两个路径都存在时返回 [global_skills, project_skills]（低到高优先级）。"""
        loader = self._make_loader(tmp_path)
        global_skills = tmp_path / "global" / ".agent-framework" / "skills"
        project_skills = tmp_path / "project" / ".agent-framework" / "skills"
        global_skills.mkdir(parents=True)
        project_skills.mkdir(parents=True)

        result = loader.discover("skills")
        assert result == [global_skills, project_skills]

    def test_only_global_exists(self, tmp_path: Path) -> None:
        """仅 global 存在 — 返回 [global_skills]。"""
        loader = self._make_loader(tmp_path)
        global_skills = tmp_path / "global" / ".agent-framework" / "skills"
        global_skills.mkdir(parents=True)

        result = loader.discover("skills")
        assert result == [global_skills]

    def test_neither_exists(self, tmp_path: Path) -> None:
        """两个都不存在 — 返回空列表 []。"""
        loader = self._make_loader(tmp_path)
        result = loader.discover("skills")
        assert result == []

    def test_unknown_type_raises_value_error(self, tmp_path: Path) -> None:
        """未知模块类型 — raise ValueError，异常信息包含 "未知模块类型: unknown_type"。"""
        loader = self._make_loader(tmp_path)
        with pytest.raises(ValueError, match="未知模块类型: unknown_type"):
            loader.discover("unknown_type")

    def test_all_eight_module_types(self, tmp_path: Path) -> None:
        """MODULE_DIRS 包含全部 8 种模块类型。"""
        expected = {
            "skills": "skills",
            "agents": "agents",
            "commands": "commands",
            "hooks": "hooks",
            "rules": "rules",
            "profiles": "profiles",
            "memory": "memory",
            "mcp": "mcp",
        }
        assert MODULE_DIRS == expected

    def test_discover_file_not_dir_skipped(self, tmp_path: Path) -> None:
        """同名文件（非目录）被跳过，不返回。"""
        loader = self._make_loader(tmp_path)
        global_af = tmp_path / "global" / ".agent-framework"
        global_af.mkdir(parents=True)
        (global_af / "skills").write_text("not a dir", encoding="utf-8")

        result = loader.discover("skills")
        assert result == []


class TestLeafDependency:
    """loader.py 叶依赖约束测试。"""

    def test_loader_does_not_import_non_config_modules(self) -> None:
        """loader.py 不导入 agent_framework 下除 config 外的任何模块。"""
        import ast

        config_dir = Path(__file__).resolve().parent.parent / "agent_framework" / "config"
        loader_file = config_dir / "loader.py"
        if not loader_file.exists():
            pytest.skip("loader.py not yet created")

        tree = ast.parse(loader_file.read_text(encoding="utf-8"))
        forbidden_prefixes = ("agent_framework.",)
        allowed_imports = ("agent_framework.config",)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if any(node.module.startswith(p) for p in forbidden_prefixes):
                    if not any(node.module.startswith(a) for a in allowed_imports):
                        pytest.fail(
                            f"loader.py imports '{node.module}' — "
                            f"must not import other framework modules"
                        )


class TestBarrelExport:
    """barrel __init__.py 导出 ConfigLoader 测试。"""

    def test_config_loader_in_all(self) -> None:
        """__all__ 包含 ConfigLoader。"""
        from agent_framework.config import __all__

        assert "ConfigLoader" in __all__

    def test_config_loader_importable(self) -> None:
        """from agent_framework.config import ConfigLoader 正常工作。"""
        from agent_framework.config import ConfigLoader as CL

        assert CL is ConfigLoader
