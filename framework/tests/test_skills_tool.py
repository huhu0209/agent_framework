"""load_skill 工具测试。"""

from pathlib import Path

import pytest

from agent_framework.skills.registry import SkillRegistry
from agent_framework.skills.tool import create_load_skill_spec
from agent_framework.tools.types import ToolUseContext


def _make_ctx(registry: SkillRegistry | None = None) -> ToolUseContext:
    extra = {}
    if registry is not None:
        extra["skill_registry"] = registry
    return ToolUseContext(extra=extra)


def _make_registry_with_skill(tmp_path: Path) -> SkillRegistry:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_path = skills_dir / "deploy"
    skill_path.mkdir()
    (skill_path / "SKILL.md").write_text(
        "---\nname: deploy\ndescription: 部署\n---\n# 部署流程", encoding="utf-8"
    )
    return SkillRegistry([skills_dir])


class TestCreateLoadSkillSpec:
    def test_spec_fields(self):
        spec = create_load_skill_spec()
        assert spec.name == "load_skill"
        assert "skill" in spec.description.lower()
        assert "name" in spec.parameters.properties
        assert "name" in spec.parameters.required
        assert spec.timeout_ms == 5_000
        assert spec.annotations.get("readOnlyHint") is True


@pytest.mark.asyncio
class TestLoadSkillHandler:
    async def test_load_existing_skill(self, tmp_path):
        registry = _make_registry_with_skill(tmp_path)
        spec = create_load_skill_spec()
        ctx = _make_ctx(registry)

        result = await spec.handler({"name": "deploy"}, ctx)
        assert not result.is_error
        assert '<skill name="deploy">' in result.content

    async def test_load_unknown_skill(self, tmp_path):
        registry = _make_registry_with_skill(tmp_path)
        spec = create_load_skill_spec()
        ctx = _make_ctx(registry)

        result = await spec.handler({"name": "nonexistent"}, ctx)
        assert result.is_error
        assert "未知" in result.content

    async def test_load_empty_name(self, tmp_path):
        registry = _make_registry_with_skill(tmp_path)
        spec = create_load_skill_spec()
        ctx = _make_ctx(registry)

        result = await spec.handler({"name": ""}, ctx)
        assert result.is_error
        assert "请指定" in result.content

    async def test_no_registry_configured(self):
        spec = create_load_skill_spec()
        ctx = _make_ctx()

        result = await spec.handler({"name": "deploy"}, ctx)
        assert result.is_error
        assert "未配置" in result.content
