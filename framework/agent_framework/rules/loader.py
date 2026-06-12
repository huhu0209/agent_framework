"""规则加载 — RuleLoader 从 ConfigLoader.discover("rules") 路径加载规则文件。"""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from agent_framework.config.loader import ConfigLoader
from agent_framework.memory.frontmatter import parse_frontmatter_lines


def _parse_rule_document(text: str) -> tuple[dict[str, str], str]:
    """解析规则 Markdown 文件，返回 (meta_dict, body_string)。

    无 frontmatter -> ({}, text)。
    frontmatter 不闭合 -> ({}, text)。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    body = "\n".join(lines[end_idx + 1:]).strip()
    meta = parse_frontmatter_lines(lines[1:end_idx])
    return meta, body


def _parse_paths(value: str | None) -> list[str] | None:
    """解析 paths 字段 — 逗号分隔的 glob 模式列表。"""
    if value is None:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


class RuleLoader:
    """规则加载器 — 从 discover("rules") 路径加载并过滤规则文件。"""

    @staticmethod
    def load_rules(
        loader: ConfigLoader,
        context_path: str | None = None,
    ) -> str:
        """加载所有匹配的规则文件，返回拼接后的规则文本。

        Args:
            loader: ConfigLoader 实例，用于发现 rules 目录。
            context_path: 当前文件路径，用于 paths frontmatter 过滤。
                None 时只加载无 paths frontmatter 的规则。

        Returns:
            双换行分隔的规则文本。
        """
        rules_dirs = loader.discover("rules")
        all_rules: list[str] = []

        for rules_dir in rules_dirs:
            for rule_file in sorted(rules_dir.glob("*.md")):
                text = rule_file.read_text(encoding="utf-8")
                meta, body = _parse_rule_document(text)

                rule_paths = _parse_paths(meta.get("paths"))

                if rule_paths is None:
                    # 无 paths frontmatter -> 始终加载
                    all_rules.append(body)
                elif context_path is not None:
                    # 有 paths 且有 context_path -> fnmatch 匹配
                    if any(fnmatch(context_path, p) for p in rule_paths):
                        all_rules.append(body)
                # 有 paths 但无 context_path -> 跳过

        return "\n\n".join(all_rules)
