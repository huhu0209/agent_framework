"""Memory 模块共享测试基础设施。"""

from __future__ import annotations

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
