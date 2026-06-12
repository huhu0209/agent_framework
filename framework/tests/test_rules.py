"""RuleLoader 单元测试 — rules 模块加载与路径过滤。"""

from pathlib import Path

import pytest

from agent_framework.config.loader import ConfigLoader
from agent_framework.rules.loader import RuleLoader


def _make_loader(tmp_path: Path, *, global_dir: Path | None = None,
                 project_dir: Path | None = None) -> ConfigLoader:
    """创建使用 tmp_path 的 ConfigLoader 实例。"""
    return ConfigLoader(
        global_dir=global_dir or tmp_path / "global",
        project_dir=project_dir or tmp_path / "project",
    )


class TestRuleLoader:
    """RuleLoader.load_rules() 测试。"""

    def test_no_rules_directories_returns_empty(self, tmp_path: Path) -> None:
        """无 rules 目录时返回空字符串。"""
        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader)
        assert result == ""

    def test_rules_without_frontmatter_loaded(self, tmp_path: Path) -> None:
        """无 frontmatter 的规则文件全部加载，以双换行拼接。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "a.md").write_text("规则 A 内容", encoding="utf-8")
        (rules_dir / "b.md").write_text("规则 B 内容", encoding="utf-8")

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader)
        assert result == "规则 A 内容\n\n规则 B 内容"

    def test_paths_frontmatter_matching_context_loads(self, tmp_path: Path) -> None:
        """paths frontmatter 匹配 context_path 时加载规则。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "scoped.md").write_text(
            "---\npaths: src/**/*.py\n---\n仅 Python 文件规则",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader, context_path="src/utils/helper.py")
        assert "仅 Python 文件规则" in result

    def test_paths_frontmatter_non_matching_context_skips(self, tmp_path: Path) -> None:
        """paths frontmatter 不匹配 context_path 时跳过规则。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "scoped.md").write_text(
            "---\npaths: src/**/*.py\n---\n仅 Python 文件规则",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader, context_path="docs/readme.md")
        assert result == ""

    def test_no_context_path_loads_unscoped_only(self, tmp_path: Path) -> None:
        """context_path=None 时只加载无 paths frontmatter 的规则（D-07 + D-12）。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "global_rule.md").write_text("全局规则", encoding="utf-8")
        (rules_dir / "scoped.md").write_text(
            "---\npaths: src/**\n---\n限定规则",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader)
        assert result == "全局规则"

    def test_discover_order_global_then_project(self, tmp_path: Path) -> None:
        """discover("rules") 按 global -> project 顺序迭代。"""
        global_rules = tmp_path / "global" / ".agent-framework" / "rules"
        global_rules.mkdir(parents=True)
        (global_rules / "base.md").write_text("全局基础规则", encoding="utf-8")

        project_rules = tmp_path / "project" / ".agent-framework" / "rules"
        project_rules.mkdir(parents=True)
        (project_rules / "override.md").write_text("项目覆盖规则", encoding="utf-8")

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader)
        assert result == "全局基础规则\n\n项目覆盖规则"

    def test_malformed_frontmatter_treated_as_no_frontmatter(self, tmp_path: Path) -> None:
        """未闭合的 frontmatter 视为无 frontmatter，加载全部内容。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "broken.md").write_text(
            "---\npaths: src/**\n未闭合的 frontmatter",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader)
        assert "---" in result
        assert "未闭合的 frontmatter" in result

    def test_comma_separated_paths_patterns(self, tmp_path: Path) -> None:
        """paths 字段逗号分隔多个模式，任一匹配即加载。"""
        rules_dir = tmp_path / "project" / ".agent-framework" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "multi.md").write_text(
            "---\npaths: src/**.py, tests/**.py\n---\n多模式规则",
            encoding="utf-8",
        )

        loader = _make_loader(tmp_path)
        result = RuleLoader.load_rules(loader, context_path="tests/test_foo.py")
        assert "多模式规则" in result
