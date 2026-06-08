"""SkillRegistry 测试。"""

import os
import shutil
from pathlib import Path

import pytest

from agent_framework.skills.registry import SkillRegistry
from agent_framework.skills.types import SkillDocument, SkillManifest, SkillSource

from tests.helpers import create_skill


class TestSkillRegistryScan:
    def test_scan_single_skill(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用", "# 部署\n步骤 1")

        registry = SkillRegistry([skills_dir])
        assert registry.get_names() == ["deploy"]

    def test_scan_multiple_skills(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署")
        create_skill(skills_dir, "review", "审查")

        registry = SkillRegistry([skills_dir])
        assert registry.get_names() == ["deploy", "review"]

    def test_scan_empty_directory(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        registry = SkillRegistry([skills_dir])
        assert registry.get_names() == []

    def test_scan_nonexistent_directory(self, tmp_path):
        registry = SkillRegistry([tmp_path / "nope"])
        assert registry.get_names() == []

    def test_priority_first_wins(self, tmp_path):
        personal = tmp_path / "personal"
        project = tmp_path / "project"
        personal.mkdir()
        project.mkdir()

        create_skill(personal, "deploy", "个人版部署")
        create_skill(project, "deploy", "项目版部署")

        registry = SkillRegistry([personal, project])
        assert len(registry.get_names()) == 1
        assert "个人版部署" in registry.load_full_text("deploy").content

    def test_missing_name_uses_directory_name(self, tmp_path, caplog):
        import logging

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "my-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\ndescription: 测试\n---\nbody", encoding="utf-8"
        )

        with caplog.at_level(logging.WARNING):
            registry = SkillRegistry([skills_dir])

        assert "my-skill" in registry.get_names()
        assert any("缺 name" in r.message for r in caplog.records)

    def test_missing_description_defaults_and_warns(self, tmp_path, caplog):
        import logging

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "test2"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: test2\n---\nbody", encoding="utf-8"
        )

        with caplog.at_level(logging.WARNING):
            registry = SkillRegistry([skills_dir])

        assert "test2" in registry.get_names()
        assert any("缺 description" in r.message for r in caplog.records)

    def test_unreadable_file_skipped(self, tmp_path, caplog):
        import logging

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        create_skill(skills_dir, "good", "正常 skill")

        bad_dir = skills_dir / "bad"
        bad_dir.mkdir()
        bad_file = bad_dir / "SKILL.md"
        bad_file.write_text("---\nname: bad\n---\nbody", encoding="utf-8")
        bad_file.chmod(0o000)

        try:
            with caplog.at_level(logging.WARNING):
                registry = SkillRegistry([skills_dir])
            assert "good" in registry.get_names()
        finally:
            bad_file.chmod(0o644)

    def test_nested_skill_directory(self, tmp_path):
        skills_dir = tmp_path / "skills"
        create_skill(skills_dir / "category", "deploy", "部署")

        registry = SkillRegistry([skills_dir])
        assert "deploy" in registry.get_names()


class TestDescribeAvailable:
    def test_format(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用")
        create_skill(skills_dir, "review", "代码审查")

        registry = SkillRegistry([skills_dir])
        catalog = registry.describe_available()

        assert "- deploy: 部署应用" in catalog
        assert "- review: 代码审查" in catalog

    def test_empty_returns_placeholder(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        registry = SkillRegistry([skills_dir])
        assert registry.describe_available() == "(没有可用的 skills)"


class TestLoadFullText:
    def test_existing_skill_returns_wrapped_body(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署", "# 部署流程\n步骤 1\n步骤 2")

        registry = SkillRegistry([skills_dir])
        result = registry.load_full_text("deploy")

        assert result.is_error is False
        assert result.content.startswith('<skill name="deploy">')
        assert "# 部署流程" in result.content
        assert result.content.strip().endswith("</skill>")

    def test_unknown_skill_returns_error_with_suggestions(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署")

        registry = SkillRegistry([skills_dir])
        result = registry.load_full_text("nonexistent")

        assert result.is_error is True
        assert "deploy" in result.content

    def test_with_references(self, tmp_path):
        skills_dir = tmp_path / "skills"
        create_skill(skills_dir, "deploy", "部署", "body")

        ref_dir = skills_dir / "deploy" / "references"
        ref_dir.mkdir()
        (ref_dir / "cli.md").write_text("# CLI 参数", encoding="utf-8")
        (ref_dir / "env.md").write_text("# 环境变量", encoding="utf-8")

        registry = SkillRegistry([skills_dir])
        result = registry.load_full_text("deploy")

        assert "references/cli.md" in result.content
        assert "references/env.md" in result.content

    def test_no_references_only_body(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署", "body text")

        registry = SkillRegistry([skills_dir])
        result = registry.load_full_text("deploy")

        assert "参考文档" not in result.content

    def test_skill_name_with_special_chars_escaped(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / 'weird"skill'
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            '---\nname: "weird\\"skill"\ndescription: test\n---\nbody',
            encoding="utf-8",
        )
        registry = SkillRegistry([skills_dir])
        result = registry.load_full_text('weird"skill')
        assert result.is_error is False
        # quoteattr wraps in single quotes when value contains double quote
        assert "name='weird\"skill'" in result.content

    def test_references_truncated_at_10(self, tmp_path):
        skills_dir = tmp_path / "skills"
        create_skill(skills_dir, "big", "大 skill", "body")

        ref_dir = skills_dir / "big" / "references"
        ref_dir.mkdir()
        for i in range(15):
            (ref_dir / f"ref-{i:02d}.md").write_text(f"ref {i}", encoding="utf-8")

        registry = SkillRegistry([skills_dir])
        result = registry.load_full_text("big")

        assert result.content.count("references/") == 10
        assert "还有 5 个文件未显示" in result.content


class TestAutoDiscovery:
    def test_new_skill_auto_discovered(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        registry = SkillRegistry([skills_dir])
        assert registry.get_names() == []

        create_skill(skills_dir, "new-skill", "新增的 skill")

        stored_mtime = registry._dir_mtimes.get(skills_dir, 0)
        os.utime(skills_dir, (stored_mtime + 1, stored_mtime + 1))

        catalog = registry.describe_available()
        assert "new-skill" in catalog

    def test_deleted_skill_removed_on_auto_refresh(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "keep", "保留")
        create_skill(skills_dir, "remove", "待删除")

        registry = SkillRegistry([skills_dir])
        assert "remove" in registry.get_names()

        shutil.rmtree(skills_dir / "remove")

        stored_mtime = registry._dir_mtimes.get(skills_dir, 0)
        os.utime(skills_dir, (stored_mtime + 1, stored_mtime + 1))

        registry.describe_available()
        assert "remove" not in registry.get_names()
        assert "keep" in registry.get_names()

    def test_forced_refresh(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "initial", "初始")

        registry = SkillRegistry([skills_dir])
        assert registry.get_names() == ["initial"]

        create_skill(skills_dir, "added", "新增")

        registry.refresh()
        assert "added" in registry.get_names()


class TestGetManifest:
    def test_existing_skill_returns_manifest(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署应用", "body")

        registry = SkillRegistry([skills_dir])
        manifest = registry.get_manifest("deploy")

        assert manifest is not None
        assert manifest.name == "deploy"
        assert manifest.description == "部署应用"
        assert manifest.user_invocable is True

    def test_nonexistent_skill_returns_none(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        registry = SkillRegistry([skills_dir])
        assert registry.get_manifest("nope") is None

    def test_user_invocable_false(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "internal", "内部 skill", "body", **{"user-invocable": "false"})

        registry = SkillRegistry([skills_dir])
        manifest = registry.get_manifest("internal")

        assert manifest is not None
        assert manifest.user_invocable is False


class TestSkillSourceTracking:
    def test_source_stored_on_manifest(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署")

        registry = SkillRegistry([skills_dir])
        manifest = registry.get_manifest("deploy")
        assert manifest is not None
        assert manifest.source == SkillSource.USER

    def test_is_trusted_user_source(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署")

        registry = SkillRegistry([skills_dir])
        assert registry.is_trusted("deploy") is True

    def test_is_not_trusted_mcp_source(self):
        manifest = SkillManifest(
            name="mcp-tool",
            description="MCP tool",
            path=Path("/tmp"),
            source=SkillSource.MCP,
        )
        registry = SkillRegistry([])
        registry._documents["mcp-tool"] = SkillDocument(manifest=manifest, body="body")
        assert registry.is_trusted("mcp-tool") is False

    def test_is_trusted_unknown_skill(self):
        registry = SkillRegistry([])
        assert registry.is_trusted("nonexistent") is False


class TestActivateForPaths:
    def test_activate_matching_skill(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "python-review"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: python-review\ndescription: Python 审查\npaths: src/**/*.py\n---\nbody",
            encoding="utf-8",
        )

        registry = SkillRegistry([skills_dir])
        doc = registry._documents.get("python-review")
        assert doc is not None
        assert doc.active is False

        activated = registry.activate_for_paths(["src/main.py"])
        assert "python-review" in activated
        assert registry._documents["python-review"].active is True

    def test_no_match_stays_inactive(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "python-review"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: python-review\ndescription: Python 审查\npaths: src/**/*.py\n---\nbody",
            encoding="utf-8",
        )

        registry = SkillRegistry([skills_dir])
        activated = registry.activate_for_paths(["frontend/App.tsx"])
        assert activated == []

    def test_describe_available_excludes_inactive(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "python-review"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: python-review\ndescription: Python 审查\npaths: src/**/*.py\n---\nbody",
            encoding="utf-8",
        )
        create_skill(skills_dir, "deploy", "部署")

        registry = SkillRegistry([skills_dir])
        catalog = registry.describe_available()
        assert "deploy" in catalog
        assert "python-review" not in catalog


class TestSkillRegistryConstructor:
    def test_empty_list(self):
        registry = SkillRegistry([])
        assert registry.get_names() == []
