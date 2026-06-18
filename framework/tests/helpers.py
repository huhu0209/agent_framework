"""测试辅助工具。"""

from __future__ import annotations

from pathlib import Path


def create_skill(
    skills_dir: Path,
    name: str,
    description: str,
    body: str = "",
    **meta_extra: str,
) -> Path:
    """在 skills_dir/name/ 下创建 SKILL.md。"""
    skill_path = skills_dir / name
    skill_path.mkdir(parents=True, exist_ok=True)

    meta_lines = ["---"]
    meta_lines.append(f"name: {name}")
    meta_lines.append(f"description: {description}")
    for k, v in meta_extra.items():
        meta_lines.append(f"{k}: {v}")
    meta_lines.append("---")

    content = "\n".join(meta_lines) + "\n" + body
    skill_file = skill_path / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file
