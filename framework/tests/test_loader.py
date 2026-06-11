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


class TestLoadAgentsMd:
    """load_agents_md() 指令链加载测试。"""

    def _make_loader(
        self, tmp_path: Path, *, global_dir: Path | None = None, project_dir: Path | None = None
    ) -> ConfigLoader:
        """创建使用 tmp_path 子目录的 ConfigLoader。"""
        g = global_dir or (tmp_path / "global")
        p = project_dir or (tmp_path / "project")
        g.mkdir(parents=True, exist_ok=True)
        p.mkdir(parents=True, exist_ok=True)
        return ConfigLoader(global_dir=g, project_dir=p)

    def _write(self, path: Path, content: str) -> None:
        """写入文件，自动创建父目录。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_full_chain_concatenation(self, tmp_path: Path) -> None:
        """Test 1: 全层级拼接 — 验证顺序和 '# Source:' 标题。"""
        loader = self._make_loader(tmp_path)

        global_af = tmp_path / "global" / ".agent-framework"
        project_af = tmp_path / "project" / ".agent-framework"
        project_root = tmp_path / "project"

        # 创建 .git 在 project_root 上层
        git_root = tmp_path / "repo"
        git_root.mkdir()
        (git_root / ".git").mkdir()
        # project 在 repo/a/b/
        project_in_repo = git_root / "a" / "b"
        project_in_repo.mkdir(parents=True)

        # 重新创建 loader 指向 repo 内的 project
        loader = ConfigLoader(global_dir=tmp_path / "global", project_dir=project_in_repo)

        global_af = tmp_path / "global" / ".agent-framework"
        project_af = project_in_repo / ".agent-framework"

        # global AGENTS.md
        self._write(global_af / "AGENTS.md", "global agents")
        # project AGENTS.md
        self._write(project_af / "AGENTS.md", "project agents")
        # project AGENTS.local.md
        self._write(project_af / "AGENTS.local.md", "local agents")
        # 父目录链: repo/a/AGENTS.md, repo/a/b/AGENTS.md
        # project_in_repo = repo/a/b, _project_dir = repo/a/b/.agent-framework
        # _parent_agents_chain: project_root = repo/a/b, git_root = repo
        # chain: [repo/a, repo/a/b] reversed -> already low-to-high from git_root
        self._write(git_root / "a" / "AGENTS.md", "parent a agents")
        self._write(git_root / "a" / "b" / "AGENTS.md", "parent b agents")
        # global user.md
        self._write(global_af / "user.md", "user content")

        result = loader.load_agents_md()

        # 验证顺序: global -> project -> local -> 父目录链 -> user
        assert "# Source: ~/.agent-framework/AGENTS.md" in result
        assert "# Source: .agent-framework/AGENTS.md" in result
        assert "# Source: .agent-framework/AGENTS.local.md" in result
        assert "# Source: ~/.agent-framework/user.md" in result

        # 验证内容
        assert "global agents" in result
        assert "project agents" in result
        assert "local agents" in result
        assert "user content" in result

        # 验证顺序: global 在 project 前面
        assert result.index("global agents") < result.index("project agents")
        assert result.index("project agents") < result.index("local agents")
        assert result.index("local agents") < result.index("user content")

    def test_only_global_agents_md(self, tmp_path: Path) -> None:
        """Test 2: 仅 global AGENTS.md — 其他文件不存在。"""
        loader = self._make_loader(tmp_path)
        global_af = tmp_path / "global" / ".agent-framework"
        self._write(global_af / "AGENTS.md", "only global")

        result = loader.load_agents_md()
        assert "# Source: ~/.agent-framework/AGENTS.md" in result
        assert "only global" in result
        assert result.count("# Source:") == 1

    def test_no_files_returns_empty(self, tmp_path: Path) -> None:
        """Test 3: 全部文件不存在 — 返回空字符串。"""
        loader = self._make_loader(tmp_path)
        result = loader.load_agents_md()
        assert result == ""

    def test_parent_chain_direction(self, tmp_path: Path) -> None:
        """Test 4: 父目录链方向 — 从 .git 根向下，低到高优先级。"""
        # repo/.git, project_dir = repo/a/b
        git_root = tmp_path / "repo"
        (git_root / ".git").mkdir(parents=True)
        project_dir = git_root / "a" / "b"
        project_dir.mkdir(parents=True)

        global_base = tmp_path / "global"
        global_base.mkdir()
        loader = ConfigLoader(global_dir=global_base, project_dir=project_dir)

        # 父目录链文件
        self._write(git_root / "a" / "AGENTS.md", "level a")
        self._write(git_root / "a" / "b" / "AGENTS.md", "level b")

        result = loader.load_agents_md()
        # level a 应在 level b 前面（低优先级在前）
        assert "level a" in result
        assert "level b" in result
        assert result.index("level a") < result.index("level b")

    def test_no_git_dir_empty_chain(self, tmp_path: Path) -> None:
        """Test 5: 无 .git 目录 — 父目录链为空，不影响其他层。"""
        loader = self._make_loader(tmp_path)
        global_af = tmp_path / "global" / ".agent-framework"
        project_af = tmp_path / "project" / ".agent-framework"
        self._write(global_af / "AGENTS.md", "global")
        self._write(project_af / "AGENTS.md", "project")

        result = loader.load_agents_md()
        assert "global" in result
        assert "project" in result
        # 无 .git，父目录链为空，只有 global + project 两个 Source
        assert result.count("# Source:") == 2

    def test_git_at_project_dir_empty_chain(self, tmp_path: Path) -> None:
        """Test 6: .git 在 project_dir 本身 — 父目录链为空。"""
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()

        global_base = tmp_path / "global"
        global_base.mkdir()
        loader = ConfigLoader(global_dir=global_base, project_dir=project_dir)

        project_af = project_dir / ".agent-framework"
        self._write(project_af / "AGENTS.md", "project only")

        result = loader.load_agents_md()
        assert result.count("# Source:") == 1
        assert "project only" in result

    def test_double_newline_separation(self, tmp_path: Path) -> None:
        """Test 7: 片段间双换行分隔。"""
        loader = self._make_loader(tmp_path)
        global_af = tmp_path / "global" / ".agent-framework"
        project_af = tmp_path / "project" / ".agent-framework"
        self._write(global_af / "AGENTS.md", "first")
        self._write(project_af / "AGENTS.md", "second")

        result = loader.load_agents_md()
        # 两个片段之间应有 "\n\n"
        assert "# Source: ~/.agent-framework/AGENTS.md\nfirst" in result
        assert "# Source: .agent-framework/AGENTS.md\nsecond" in result
        # 验证片段间是 "\n\n"
        assert "first\n\n# Source:" in result

    def test_source_header_format(self, tmp_path: Path) -> None:
        """Test 8: '# Source:' 标题格式 — 每个片段以 '# Source: <label>\\n' 开头。"""
        loader = self._make_loader(tmp_path)
        global_af = tmp_path / "global" / ".agent-framework"
        self._write(global_af / "AGENTS.md", "content")
        self._write(global_af / "user.md", "user info")

        result = loader.load_agents_md()
        lines = result.split("\n")
        # 第一个非空行应为 # Source:
        first_non_empty = next(line for line in lines if line.strip())
        assert first_non_empty.startswith("# Source:")

    def test_empty_content_file_skipped(self, tmp_path: Path) -> None:
        """Test 9: 空内容文件跳过 — 文件存在但内容为空白。"""
        loader = self._make_loader(tmp_path)
        global_af = tmp_path / "global" / ".agent-framework"
        self._write(global_af / "AGENTS.md", "   \n  \n  ")
        project_af = tmp_path / "project" / ".agent-framework"
        self._write(project_af / "AGENTS.md", "real content")

        result = loader.load_agents_md()
        assert result.count("# Source:") == 1
        assert "real content" in result


class TestLoadProfile:
    """load_profile() 双路径合并 Profile 加载测试。"""

    PROFILE_FILES = ["soul.md", "agents.md", "identity.md", "tool_guidance.md"]

    def _make_loader(self, tmp_path: Path) -> ConfigLoader:
        """创建使用 tmp_path 的 ConfigLoader。"""
        global_base = tmp_path / "global"
        project_base = tmp_path / "project"
        global_base.mkdir(parents=True, exist_ok=True)
        project_base.mkdir(parents=True, exist_ok=True)
        return ConfigLoader(global_dir=global_base, project_dir=project_base)

    def _write(self, path: Path, content: str) -> None:
        """写入文件，自动创建父目录。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _global_profile_dir(self, tmp_path: Path, name: str = "default") -> Path:
        return tmp_path / "global" / ".agent-framework" / "profiles" / name

    def _project_profile_dir(self, tmp_path: Path, name: str = "default") -> Path:
        return tmp_path / "project" / ".agent-framework" / "profiles" / name

    def test_only_global_profile(self, tmp_path: Path) -> None:
        """Test 1: 仅 global profile — 返回全部 4 个字段。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        self._write(g / "soul.md", "global soul")
        self._write(g / "agents.md", "global agents")
        self._write(g / "identity.md", "global identity")
        self._write(g / "tool_guidance.md", "global tools")

        result = loader.load_profile("default")
        assert result == {
            "soul": "global soul",
            "agents": "global agents",
            "identity": "global identity",
            "tool_guidance": "global tools",
        }

    def test_project_overrides_global(self, tmp_path: Path) -> None:
        """Test 2: global + project 合并 — project 非空字段覆盖 global。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        p = self._project_profile_dir(tmp_path)
        self._write(g / "soul.md", "global soul")
        self._write(p / "soul.md", "project soul")

        result = loader.load_profile("default")
        assert result["soul"] == "project soul"

    def test_project_nonempty_overrides_global_empty(self, tmp_path: Path) -> None:
        """Test 3: project 非空覆盖 global 空。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        p = self._project_profile_dir(tmp_path)
        self._write(g / "soul.md", "")
        self._write(p / "soul.md", "has value")

        result = loader.load_profile("default")
        assert result["soul"] == "has value"

    def test_project_empty_does_not_override_global(self, tmp_path: Path) -> None:
        """Test 4: project 空不覆盖 global 非空。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        p = self._project_profile_dir(tmp_path)
        self._write(g / "soul.md", "global value")
        self._write(p / "soul.md", "")

        result = loader.load_profile("default")
        assert result["soul"] == "global value"

    def test_neither_path_exists(self, tmp_path: Path) -> None:
        """Test 5: 两个路径都不存在 profile — 返回空 dict。"""
        loader = self._make_loader(tmp_path)
        result = loader.load_profile("nonexistent")
        assert result == {}

    def test_partial_subfiles(self, tmp_path: Path) -> None:
        """Test 6: 只有部分子文件 — 只有存在的字段。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        self._write(g / "soul.md", "only soul")

        result = loader.load_profile("default")
        assert result == {"soul": "only soul"}
        assert "identity" not in result

    def test_four_subfile_names(self, tmp_path: Path) -> None:
        """Test 7: 4 种子文件名确认 — soul/agents/identity/tool_guidance。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        for filename in self.PROFILE_FILES:
            self._write(g / filename, f"content of {filename}")

        result = loader.load_profile("default")
        expected_keys = {"soul", "agents", "identity", "tool_guidance"}
        assert set(result.keys()) == expected_keys

    def test_returns_dict_str_str(self, tmp_path: Path) -> None:
        """Test 8: 返回类型 dict[str, str] — key 为去掉 .md 后缀的文件名。"""
        loader = self._make_loader(tmp_path)
        g = self._global_profile_dir(tmp_path)
        self._write(g / "soul.md", "soul content")

        result = loader.load_profile("default")
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result)
        assert all(isinstance(v, str) for v in result.values())
        assert "soul" in result
