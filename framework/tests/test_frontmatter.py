"""frontmatter 解析测试。"""

from agent_framework.memory.frontmatter import parse_frontmatter


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
