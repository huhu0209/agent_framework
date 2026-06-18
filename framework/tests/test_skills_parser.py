"""Skills parser — SKILL.md 解析测试。"""

from agent_framework.skills.parser import (
    _parse_bool,
    _parse_list,
    _parse_paths,
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
        assert body == text

    def test_empty_body(self):
        meta, body = _parse_skill_document("---\nname: test\n---\n")
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
        meta, _ = _parse_skill_document("---\ndescription: why: because\n---\nbody")
        assert meta["description"] == "why: because"

    def test_quoted_value(self):
        meta, _ = _parse_skill_document('---\ndescription: "has: colon"\n---\nbody')
        assert meta["description"] == "has: colon"

    def test_multiline_body(self):
        _, body = _parse_skill_document("---\nname: test\n---\nline1\nline2\nline3")
        assert body == "line1\nline2\nline3"


class TestParseBool:
    def test_true_variants(self):
        for v in ["true", "True", "TRUE", "yes", "1"]:
            assert _parse_bool(v, False) is True

    def test_false_variants(self):
        for v in ["false", "False", "no", "0"]:
            assert _parse_bool(v, True) is False

    def test_none_returns_default(self):
        assert _parse_bool(None, True) is True
        assert _parse_bool(None, False) is False

    def test_unrecognized_returns_default(self):
        assert _parse_bool("maybe", True) is True
        assert _parse_bool("maybe", False) is False


class TestParseList:
    def test_comma_separated(self):
        assert _parse_list("Read, Bash, Grep") == ["Read", "Bash", "Grep"]

    def test_none_returns_none(self):
        assert _parse_list(None) is None

    def test_empty_returns_none(self):
        assert _parse_list("") is None


class TestParsePaths:
    def test_single_pattern(self):
        assert _parse_paths("src/**/*.py") == ["src/**/*.py"]

    def test_comma_separated(self):
        assert _parse_paths("src/**/*.py, tests/**/*.py") == [
            "src/**/*.py",
            "tests/**/*.py",
        ]

    def test_none_returns_none(self):
        assert _parse_paths(None) is None

    def test_empty_returns_none(self):
        assert _parse_paths("") is None
