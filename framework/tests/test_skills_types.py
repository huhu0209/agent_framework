"""Skills types.py — 新类型定义测试。"""

from pathlib import Path

import pytest

from agent_framework.skills.types import (
    SkillDocument,
    SkillLoadResult,
    SkillManifest,
    SkillSource,
)


class TestSkillSource:
    def test_values(self):
        assert SkillSource.USER == "user"
        assert SkillSource.PROJECT == "project"
        assert SkillSource.BUNDLED == "bundled"
        assert SkillSource.MCP == "mcp"


class TestSkillManifest:
    def test_required_fields(self):
        m = SkillManifest(
            name="deploy",
            description="部署应用",
            path=Path("/tmp/deploy"),
            source=SkillSource.USER,
        )
        assert m.name == "deploy"
        assert m.source == SkillSource.USER

    def test_defaults(self):
        m = SkillManifest(
            name="test", description="desc", path=Path("/tmp"), source=SkillSource.PROJECT
        )
        assert m.user_invocable is True
        assert m.allowed_tools is None
        assert m.model is None
        assert m.disable_model_invocation is False
        assert m.context is None
        assert m.paths is None
        assert m.hooks is None

    def test_new_fields(self):
        m = SkillManifest(
            name="test",
            description="desc",
            path=Path("/tmp"),
            source=SkillSource.BUNDLED,
            disable_model_invocation=True,
            context="fork",
            paths=["src/**/*.py"],
        )
        assert m.disable_model_invocation is True
        assert m.context == "fork"
        assert m.paths == ["src/**/*.py"]

    def test_frozen(self):
        m = SkillManifest(
            name="test", description="desc", path=Path("/tmp"), source=SkillSource.USER
        )
        with pytest.raises(AttributeError):
            m.name = "other"


class TestSkillDocument:
    def test_active_default_true(self):
        m = SkillManifest(
            name="test", description="desc", path=Path("/tmp"), source=SkillSource.USER
        )
        doc = SkillDocument(manifest=m, body="body")
        assert doc.active is True

    def test_active_can_be_false(self):
        m = SkillManifest(
            name="test", description="desc", path=Path("/tmp"), source=SkillSource.USER
        )
        doc = SkillDocument(manifest=m, body="body", active=False)
        assert doc.active is False


class TestSkillLoadResult:
    def test_success(self):
        r = SkillLoadResult(content="ok")
        assert r.is_error is False

    def test_error(self):
        r = SkillLoadResult(content="fail", is_error=True)
        assert r.is_error is True
