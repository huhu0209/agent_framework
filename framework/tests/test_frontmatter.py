"""frontmatter 解析与生成测试。"""

from agent_framework.memory.frontmatter import format_frontmatter, parse_frontmatter


class TestParseFrontmatter:
    def test_standard_frontmatter(self):
        text = "---\nname: test\ndescription: 测试\n---\nbody"
        result = parse_frontmatter(text)
        assert result == {"name": "test", "description": "测试"}

    def test_no_frontmatter(self):
        text = "# Title\nbody"
        assert parse_frontmatter(text) == {}

    def test_value_with_colon(self):
        text = "---\nurl: https://example.com:8080\n---\n"
        result = parse_frontmatter(text)
        assert result == {"url": "https://example.com:8080"}

    def test_empty_frontmatter_block(self):
        text = "---\n---\nbody"
        assert parse_frontmatter(text) == {}

    def test_empty_input(self):
        assert parse_frontmatter("") == {}


class TestQuotedValueParsing:
    """parse_frontmatter 应正确处理双引号包裹的值（与 format_frontmatter 对称）。"""

    def test_double_quoted_value_with_colon(self):
        text = '---\ndescription: "why: because..."\n---\n'
        result = parse_frontmatter(text)
        assert result == {"description": "why: because..."}

    def test_double_quoted_value_with_escape(self):
        text = '---\nname: "contains \\"quotes\\""\n---\n'
        result = parse_frontmatter(text)
        assert result == {"name": 'contains "quotes"'}

    def test_double_quoted_value_with_backslash(self):
        text = '---\npath: "C:\\\\Users\\\\test"\n---\n'
        result = parse_frontmatter(text)
        assert result == {"path": "C:\\Users\\test"}

    def test_unquoted_value_unchanged(self):
        text = "---\nname: simple\n---\n"
        result = parse_frontmatter(text)
        assert result == {"name": "simple"}

    def test_empty_quoted_value(self):
        text = '---\nname: ""\n---\n'
        result = parse_frontmatter(text)
        assert result == {"name": ""}

    def test_roundtrip_with_special_chars(self):
        meta = {"name": "测试", "description": "why: 因为这样更好"}
        text = format_frontmatter(meta)
        result = parse_frontmatter(text)
        assert result == meta


class TestFormatFrontmatter:
    def test_normal_keys(self):
        result = format_frontmatter({"name": "test", "type": "user"})
        assert result.startswith("---\n")
        assert result.endswith("\n---")
        assert "name: test" in result
        assert "type: user" in result

    def test_special_chars_quoted(self):
        result = format_frontmatter({"desc": "has: colon"})
        assert '"has: colon"' in result

    def test_empty_dict(self):
        result = format_frontmatter({})
        assert result == "---\n---"
