"""验证循环 — Post-Tool 和 Post-Turn 两个时机。"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel


class VerificationRule(BaseModel):
    """一条验证规则。"""

    name: str
    description: str
    # B1: 仅 regex_match 已实现。未实现类型（code_compiles/tests_pass/schema_valid/llm_judge）
    # 之前在 _run_single 中 return None 被静默跳过（安全幻觉），现收紧到 schema 层拒绝。
    # 扩展点：实现新 check 类型时在此 Literal 添加该值，并在 _run_single 加对应分支。
    check: Literal["regex_match"]
    config: dict[str, Any] = {}
    tool_names: list[str] | None = None  # None = 所有工具


class VerificationResult(BaseModel):
    """一条验证结果。"""

    rule: str
    passed: bool
    detail: str


class VerificationRunner:
    """执行验证规则。"""

    def __init__(self, rules: list[VerificationRule]) -> None:
        self._rules = rules

    def run_post_tool(self, tool_name: str, tool_input: dict) -> list[VerificationResult]:
        """运行适用于指定工具的 Post-Tool 验证规则。"""
        results = []
        for rule in self._rules:
            if rule.tool_names is not None and tool_name not in rule.tool_names:
                continue

            result = self._run_single(rule, tool_input)
            if result is not None:
                results.append(result)

        return results

    def _run_single(self, rule: VerificationRule, tool_input: dict) -> VerificationResult | None:
        """执行单条规则。"""
        if rule.check == "regex_match":
            return self._check_regex(rule, tool_input)

        return None

    def _check_regex(self, rule: VerificationRule, tool_input: dict) -> VerificationResult:
        """正则匹配验证。"""
        field = rule.config.get("field", "")
        pattern = rule.config.get("pattern", "")
        value = str(tool_input.get(field, ""))

        # B2: 空 pattern 会导致 re.search("", any) 恒匹配（永远 passed=True），验证形同虚设
        if not pattern:
            return VerificationResult(
                rule=rule.name,
                passed=False,
                detail="规则缺少 pattern 配置",
            )

        # B2: 非法 pattern 抛 re.error 会中断工具执行，降级为失败结果
        try:
            matched = bool(re.search(pattern, value))
        except re.error as exc:
            return VerificationResult(
                rule=rule.name,
                passed=False,
                detail=f"非法正则模式 '{pattern}': {exc}",
            )

        if matched:
            return VerificationResult(rule=rule.name, passed=True, detail="匹配成功")

        return VerificationResult(
            rule=rule.name,
            passed=False,
            detail=f"字段 '{field}' 不匹配模式 '{pattern}'",
        )
