"""Frontmatter 解析与生成工具。"""

from __future__ import annotations


def parse_frontmatter(text: str) -> dict[str, str]:
    """解析 Markdown 文件的 YAML frontmatter，返回键值对。

    仅支持扁平键值对（name: value 格式），不依赖 YAML 库。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}

    result: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()

    return result
