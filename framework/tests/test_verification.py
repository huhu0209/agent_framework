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


class TestUnimplementedCheckTypes:
    """B1: 未实现的 check 类型必须在 schema 层被拒绝，而非静默 no-op。"""

    def test_code_compiles_rejected(self):
        """B1: code_compiles 未实现，构造时应 ValidationError。"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VerificationRule(
                name="compile_check",
                description="编译检查",
                check="code_compiles",
                config={},
            )

    def test_tests_pass_rejected(self):
        """B1: tests_pass 未实现，构造时 ValidationError。"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VerificationRule(
                name="test_check",
                description="测试检查",
                check="tests_pass",
                config={},
            )

    def test_regex_match_still_accepted(self):
        """B1: regex_match 仍可正常构造（唯一已实现类型）。"""
        rule = VerificationRule(
            name="ok",
            description="正则",
            check="regex_match",
            config={"pattern": ".+"},
        )
        assert rule.check == "regex_match"


class TestRegexPatternRobustness:
    """B2: 空 pattern 不能恒匹配，非法 pattern 不能崩溃。"""

    def test_empty_pattern_fails_not_matches(self):
        """B2: 空 pattern 应返回 passed=False（规则缺配置），而非恒匹配。"""
        rule = VerificationRule(
            name="need_pattern",
            description="需要 pattern",
            check="regex_match",
            config={"field": "content"},  # 故意不配 pattern
        )
        runner = VerificationRunner(rules=[rule])

        results = runner.run_post_tool("write_file", {"content": "anything"})
        assert len(results) == 1
        assert not results[0].passed
        assert "pattern" in results[0].detail  # 提示缺 pattern 配置

    def test_invalid_pattern_fails_not_raises(self):
        """B2: 非法 pattern 应返回 passed=False，不抛 re.error。"""
        rule = VerificationRule(
            name="bad_regex",
            description="非法正则",
            check="regex_match",
            config={"field": "content", "pattern": "("},  # 未闭合分组
        )
        runner = VerificationRunner(rules=[rule])

        # 不应抛 re.error，返回失败结果
        results = runner.run_post_tool("write_file", {"content": "test"})
        assert len(results) == 1
        assert not results[0].passed

    def test_valid_pattern_still_works(self):
        """B2: 合法 pattern 正常匹配（回归保护）。"""
        rule = VerificationRule(
            name="ok",
            description="合法",
            check="regex_match",
            config={"field": "content", "pattern": r"\d+"},
        )
        runner = VerificationRunner(rules=[rule])

        results = runner.run_post_tool("write_file", {"content": "abc 123"})
        assert len(results) == 1
        assert results[0].passed
