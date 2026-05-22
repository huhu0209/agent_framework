"""验证循环测试。"""

import pytest

from agent_framework.safety.verification import (
    VerificationResult,
    VerificationRule,
    VerificationRunner,
)


class TestVerificationRule:
    def test_create_regex_rule(self):
        rule = VerificationRule(
            name="no_empty_file",
            description="写入文件不能为空",
            check="regex_match",
            config={"pattern": r".+", "field": "content"},
        )
        assert rule.check == "regex_match"

    def test_rule_with_tool_names(self):
        rule = VerificationRule(
            name="write_check",
            description="只检查 write_file",
            check="regex_match",
            config={"pattern": r".+"},
            tool_names=["write_file"],
        )
        assert rule.tool_names == ["write_file"]

    def test_rule_default_tool_names(self):
        rule = VerificationRule(
            name="global",
            description="全局",
            check="regex_match",
            config={"pattern": r".+"},
        )
        assert rule.tool_names is None


class TestVerificationRunner:
    def test_regex_match_pass(self):
        rule = VerificationRule(
            name="has_content",
            description="检查内容非空",
            check="regex_match",
            config={"pattern": r".{10,}", "field": "content"},
        )
        runner = VerificationRunner(rules=[rule])

        results = runner.run_post_tool("write_file", {"content": "Hello World! This is a test."})
        assert all(r.passed for r in results)

    def test_regex_match_fail(self):
        rule = VerificationRule(
            name="has_content",
            description="检查内容非空",
            check="regex_match",
            config={"pattern": r".{10,}", "field": "content"},
        )
        runner = VerificationRunner(rules=[rule])

        results = runner.run_post_tool("write_file", {"content": "Hi"})
        assert len(results) == 1
        assert not results[0].passed

    def test_no_matching_rules(self):
        runner = VerificationRunner(rules=[])
        results = runner.run_post_tool("write_file", {"content": "test"})
        assert results == []

    def test_tool_name_filter(self):
        rule = VerificationRule(
            name="write_only",
            description="只检查 write_file",
            check="regex_match",
            config={"pattern": r".+", "field": "content"},
            tool_names=["write_file"],
        )
        runner = VerificationRunner(rules=[rule])

        results = runner.run_post_tool("read_file", {"content": "test"})
        assert results == []

        results = runner.run_post_tool("write_file", {"content": "hello"})
        assert len(results) == 1

    def test_multiple_rules(self):
        rules = [
            VerificationRule(
                name="not_empty",
                description="内容非空",
                check="regex_match",
                config={"pattern": r".+", "field": "content"},
            ),
            VerificationRule(
                name="has_description",
                description="需要 description 字段",
                check="regex_match",
                config={"pattern": r".{5,}", "field": "description"},
            ),
        ]
        runner = VerificationRunner(rules=rules)

        results = runner.run_post_tool("write_file", {"content": "ok", "description": "hi"})
        assert len(results) == 2
        assert results[0].passed
        assert not results[1].passed
