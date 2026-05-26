"""Skills manifest 数据模型与文档解析测试。"""

from pathlib import Path

import pytest

from agent_framework.skills.manifest import (
    SkillDocument,
    SkillManifest,
    _parse_bool,
    _parse_list,
    _parse_skill_document,
)


class TestParseSkillDocument:
    def test_standard_frontmatter_with_body(self):
        text = "---\nname: deploy\ndescription: 部署应用\n---\n# 部署流程\n步骤 1"
        meta, body = _parse_skill_document(text)
        assert meta == {"name": "deploy", "description": "部署应用"}
        assert body == "# 部署流程\n步骤 1"

    def test_no_frontmatter(self):
        text = "# Just a body\nno frontmatter here"
        meta, body = _parse_skill_document(text)
        assert meta == {}
        assert body == "# Just a body\nno frontmatter here"

    def test_empty_body(self):
        text = "---\nname: test\n---\n"
        meta, body = _parse_skill_document(text)
        assert meta == {"name": "test"}
        assert body == ""

    def test_unclosed_frontmatter(self):
        text = "---\nname: test\nno closing"
        meta, body = _parse_skill_document(text)
        assert meta == {}
        assert body == text

    def test_empty_input(self):
        meta, body = _parse_skill_document("")
        assert meta == {}
        assert body == ""

    def test_value_with_colon(self):
        text = "---\ndescription: why: because\n---\nbody"
        meta, body = _parse_skill_document(text)
        assert meta["description"] == "why: because"

    def test_quoted_value(self):
        text = '---\ndescription: "has: colon"\n---\nbody'
        meta, body = _parse_skill_document(text)
        assert meta["description"] == "has: colon"

    def test_multiline_body(self):
        text = "---\nname: test\n---\nline1\nline2\nline3"
        meta, body = _parse_skill_document(text)
        assert body == "line1\nline2\nline3"


class TestParseBool:
    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "yes", "1"])
    def test_true_variants(self, value):
        assert _parse_bool(value, False) is True

    @pytest.mark.parametrize("value", ["false", "False", "no", "0"])
    def test_false_variants(self, value):
        assert _parse_bool(value, True) is False

    def test_none_returns_default(self):
        assert _parse_bool(None, True) is True
        assert _parse_bool(None, False) is False

    def test_unrecognized_value_returns_default(self):
        assert _parse_bool("maybe", True) is True
        assert _parse_bool("maybe", False) is False


class TestParseList:
    def test_comma_separated(self):
        assert _parse_list("Read, Bash, Grep") == ["Read", "Bash", "Grep"]

    def test_single_value(self):
        assert _parse_list("Read") == ["Read"]

    def test_none_returns_none(self):
        assert _parse_list(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_list("") is None

    def test_whitespace_handling(self):
        assert _parse_list(" Read ,  Bash ") == ["Read", "Bash"]


class TestSkillManifest:
    def test_defaults(self):
        m = SkillManifest(name="test", description="desc", path=Path("/tmp"))
        assert m.user_invocable is True
        assert m.allowed_tools is None
        assert m.model is None
        assert m.hooks is None

    def test_all_fields(self):
        m = SkillManifest(
            name="deploy",
            description="desc",
            path=Path("/tmp"),
            user_invocable=False,
            allowed_tools=["Bash", "Read"],
            model="claude-haiku-4-5",
        )
        assert m.user_invocable is False
        assert m.allowed_tools == ["Bash", "Read"]
        assert m.model == "claude-haiku-4-5"


class TestSkillDocument:
    def test_basic(self):
        manifest = SkillManifest(name="test", description="desc", path=Path("/tmp"))
        doc = SkillDocument(manifest=manifest, body="body text")
        assert doc.manifest.name == "test"
        assert doc.body == "body text"
