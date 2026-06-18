"""merge_settings() 合并引擎测试。"""

from __future__ import annotations

import copy

from agent_framework.config.merge import merge_settings


class TestMergeEmpty:
    """空输入和空 dict 测试。"""

    def test_no_args_returns_empty(self) -> None:
        """merge_settings() 无参数返回空 dict。"""
        assert merge_settings() == {}

    def test_empty_dict_returns_empty(self) -> None:
        """merge_settings({}) 返回空 dict。"""
        assert merge_settings({}) == {}


class TestMergeScalar:
    """标量覆盖测试。"""

    def test_two_levels(self) -> None:
        """两级标量覆盖。"""
        result = merge_settings({"model": "a"}, {"model": "b"})
        assert result == {"model": "b"}

    def test_three_levels(self) -> None:
        """三级标量覆盖。"""
        result = merge_settings(
            {"model": "a"}, {"model": "b"}, {"model": "c"}
        )
        assert result == {"model": "c"}

    def test_scalar_keeps_low_priority(self) -> None:
        """高优先级无该 key 时保持低优先级值。"""
        result = merge_settings({"model": "a", "level": "1"}, {"model": "b"})
        assert result == {"model": "b", "level": "1"}


class TestMergeDict:
    """dict 递归浅合并测试。"""

    def test_shallow_merge(self) -> None:
        """dict 浅合并 — 低优先级的 key 保留。"""
        result = merge_settings(
            {"llm": {"provider": "x", "timeout": 30}},
            {"llm": {"provider": "y"}},
        )
        assert result == {"llm": {"provider": "y", "timeout": 30}}

    def test_nested_dict_merge(self) -> None:
        """嵌套 dict 合并。"""
        result = merge_settings(
            {"a": {"b": {"c": 1}}},
            {"a": {"b": {"d": 2}}},
        )
        assert result == {"a": {"b": {"c": 1, "d": 2}}}


class TestMergeList:
    """list[str] 并集去重保序测试。"""

    def test_union_dedup(self) -> None:
        """并集去重 — 重复元素只保留一个。"""
        result = merge_settings({"allow": ["a", "b"]}, {"allow": ["b", "c"]})
        assert result == {"allow": ["a", "b", "c"]}

    def test_order_low_to_high(self) -> None:
        """低优先级在前、高优先级在后。"""
        result = merge_settings({"allow": ["a"]}, {"allow": ["b"]})
        assert result == {"allow": ["a", "b"]}

    def test_case_sensitive_dedup(self) -> None:
        """严格字符串全等去重 — 大小写不同不去重。"""
        result = merge_settings(
            {"allow": ["Bash(git *)"]}, {"allow": ["bash(git *)"]}
        )
        assert result == {"allow": ["Bash(git *)", "bash(git *)"]}

    def test_all_duplicates(self) -> None:
        """全部重复时去重。"""
        result = merge_settings({"items": ["a", "b"]}, {"items": ["a", "b"]})
        assert result == {"items": ["a", "b"]}


class TestMergeNestedList:
    """嵌套 dict 中 list 并集测试。"""

    def test_nested_list_union(self) -> None:
        """嵌套 permissions.allow 正确并集。"""
        result = merge_settings(
            {"permissions": {"allow": ["a"]}},
            {"permissions": {"allow": ["b"]}},
        )
        assert result == {"permissions": {"allow": ["a", "b"]}}

    def test_nested_dict_and_list_combined(self) -> None:
        """嵌套 dict 中同时有 list 和 scalar 字段。"""
        result = merge_settings(
            {"permissions": {"allow": ["a"], "deny": ["x"]}},
            {"permissions": {"allow": ["b"], "deny": ["y"]}},
        )
        assert result == {"permissions": {"allow": ["a", "b"], "deny": ["x", "y"]}}


class TestMergeMixedTypes:
    """混合类型覆盖测试。"""

    def test_list_to_scalar(self) -> None:
        """list -> scalar 类型不一致时高优先级覆盖。"""
        result = merge_settings({"key": [1, 2]}, {"key": "scalar"})
        assert result == {"key": "scalar"}

    def test_scalar_to_list(self) -> None:
        """scalar -> list 类型不一致时高优先级覆盖。"""
        result = merge_settings({"key": "scalar"}, {"key": [1, 2]})
        assert result == {"key": [1, 2]}

    def test_dict_to_scalar(self) -> None:
        """dict -> scalar 类型不一致时高优先级覆盖。"""
        result = merge_settings({"key": {"a": 1}}, {"key": "replaced"})
        assert result == {"key": "replaced"}


class TestMergeImmutability:
    """不修改输入 dict 测试。"""

    def test_does_not_modify_input(self) -> None:
        """merge_settings 不修改任何输入 dict。"""
        d1 = {"model": "a", "llm": {"provider": "x"}}
        d2 = {"model": "b", "llm": {"timeout": 30}}
        d1_copy = copy.deepcopy(d1)
        d2_copy = copy.deepcopy(d2)

        result = merge_settings(d1, d2)
        assert d1 == d1_copy
        assert d2 == d2_copy
        assert result == {"model": "b", "llm": {"provider": "x", "timeout": 30}}


class TestMergeIntegration:
    """完整集成场景测试。"""

    def test_global_project_local(self) -> None:
        """global + project + local 三级合并。"""
        global_cfg = {
            "model": "claude-sonnet-4-20250514",
            "llm": {"provider": "anthropic", "api_key": "", "base_url": None},
            "permissions": {"allow": ["Read(*)"], "deny": []},
        }
        project_cfg = {
            "model": "gpt-4",
            "llm": {"api_key": "sk-project"},
            "permissions": {"allow": ["Bash(git *)"]},
        }
        local_cfg = {
            "llm": {"api_key": "sk-local"},
            "permissions": {"allow": ["Write(*)"]},
        }
        result = merge_settings(global_cfg, project_cfg, local_cfg)
        assert result["model"] == "gpt-4"
        assert result["llm"]["provider"] == "anthropic"
        assert result["llm"]["api_key"] == "sk-local"
        assert "Read(*)" in result["permissions"]["allow"]
        assert "Bash(git *)" in result["permissions"]["allow"]
        assert "Write(*)" in result["permissions"]["allow"]
        assert result["permissions"]["deny"] == []
