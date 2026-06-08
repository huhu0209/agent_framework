"""Skills discovery — 动态激活测试。"""

from pathlib import Path

import pytest

from agent_framework.skills.discovery import SkillDiscovery
from agent_framework.skills.registry import SkillRegistry

from tests.helpers import create_skill


class TestSkillDiscovery:
    def test_activate_on_match(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "python-review"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: python-review\ndescription: 审查\npaths: src/**/*.py\n---\nbody",
            encoding="utf-8",
        )

        registry = SkillRegistry([skills_dir])
        discovery = SkillDiscovery(registry)
        activated = discovery.on_file_access("src/main.py")

        assert "python-review" in activated
        assert registry._documents["python-review"].active is True

    def test_no_match_returns_empty(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "python-review"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: python-review\ndescription: 审查\npaths: src/**/*.py\n---\nbody",
            encoding="utf-8",
        )

        registry = SkillRegistry([skills_dir])
        discovery = SkillDiscovery(registry)
        activated = discovery.on_file_access("frontend/App.tsx")

        assert activated == []

    def test_already_active_not_returned(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_skill(skills_dir, "deploy", "部署")

        registry = SkillRegistry([skills_dir])
        discovery = SkillDiscovery(registry)
        activated = discovery.on_file_access("any/file.txt")

        assert activated == []

    def test_multiple_skills_activated(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        for name, pattern in [("py-review", "src/**/*.py"), ("ts-review", "src/**/*.ts")]:
            p = skills_dir / name
            p.mkdir()
            (p / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {name}\npaths: {pattern}\n---\nbody",
                encoding="utf-8",
            )

        registry = SkillRegistry([skills_dir])
        discovery = SkillDiscovery(registry)
        activated = discovery.on_file_access("src/main.py")

        assert "py-review" in activated
        assert "ts-review" not in activated

    def test_empty_registry(self):
        registry = SkillRegistry([])
        discovery = SkillDiscovery(registry)
        activated = discovery.on_file_access("any/file.py")
        assert activated == []
