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
