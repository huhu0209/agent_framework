"""共享测试基础设施。"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_framework.llm.types import CompletionConfig, CompletionResult, StopReason, TextBlock, UsageStats


class MockAdapter:
    """最小 mock LLM adapter，返回预设文本。"""

    def __init__(self, response_text: str) -> None:
        self._response = response_text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="test-id",
            model=config.model,
            content=[TextBlock(text=self._response)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=100, output_tokens=50),
        )


@pytest.fixture
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    return d


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
