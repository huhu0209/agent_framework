"""Frontmatter 解析与生成工具。"""

from __future__ import annotations


def _yaml_string(s: str) -> str:
    """Quote a string for YAML frontmatter if it contains special chars."""
    if not s:
        return '""'
    needs_quoting = any(c in s for c in (
        ":", "'", '"', "#", "&", "*", "?", "|", "-", "<", ">",
        "=", "!", "%", "@", "`", ",", "{", "}", "[", "]",
    ))
    if "\n" in s or ": " in s or s.startswith("---"):
        needs_quoting = True
    if needs_quoting:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def format_frontmatter(meta: dict[str, str]) -> str:
    """将键值对格式化为 YAML frontmatter 块。"""
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {_yaml_string(v)}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter_lines(lines: list[str]) -> dict[str, str]:
    """解析 key:value 格式的行列表（不含 --- 分隔符）。"""
    result: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
            result[key.strip()] = value
    return result


def parse_frontmatter(text: str) -> dict[str, str]:
    """解析 Markdown 文件的 YAML frontmatter，返回键值对。

    仅支持扁平键值对（name: value 格式），不依赖 YAML 库。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    return parse_frontmatter_lines(lines[1:])
