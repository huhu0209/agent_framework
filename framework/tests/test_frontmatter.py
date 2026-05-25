"""frontmatter 工具测试。"""

from agent_framework.memory.frontmatter import parse_frontmatter


class TestParseFrontmatter:
    def test_parses_name_and_description(self):
        text = "---\nname: 测试\ndescription: 描述内容\ntype: feedback\n---\n\n正文"
        result = parse_frontmatter(text)
        assert result["name"] == "测试"
        assert result["description"] == "描述内容"
        assert result["type"] == "feedback"

    def test_no_frontmatter(self):
        assert parse_frontmatter("just some content") == {}

    def test_empty_frontmatter(self):
        assert parse_frontmatter("---\n---\n\n正文") == {}

    def test_value_with_colon(self):
        result = parse_frontmatter("---\nname: key: value\n---\n")
        assert result["name"] == "key: value"

    def test_value_with_quotes(self):
        result = parse_frontmatter("---\ndescription: has 'quotes' and \"dquotes\"\n---\n")
        assert "quotes" in result["description"]
