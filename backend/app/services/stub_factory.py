"""Stub AgentFactory — E2E 测试用，产生固定 LoopEvent 序列（不调真实 LLM）。

受环境变量 APP_AGENT_BACKEND=stub 启用，让 Playwright E2E 能跑完整 WS 流程
（config/system_prompt/工具链实时增长）而不依赖真实 LLM key/网络。
生产绝不启用。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, AsyncGenerator

from agent_framework.agents.agent_loop import LoopEvent

# 固定事件序列：1 次工具调用 + 完成（让 E2E 能验证工具链实时增长）
_STUB_EVENTS: list[LoopEvent] = [
    LoopEvent(type="step", step=1, data={"stop_reason": "tool_use", "content": []}),
    LoopEvent(
        type="tool_result", step=1, data={
            "tool_calls": [{"id": "stub_tc_1", "name": "search", "input": {"q": "e2e-query"}}],
            "tool_results": ["stub search result"],
        },
    ),
    LoopEvent(
        type="step", step=2,
        data={"stop_reason": "end_turn", "content": [{"type": "text", "text": "stub done"}]},
    ),
    LoopEvent(type="done", step=2, data={"content": [{"type": "text", "text": "stub done"}]}),
]


class _StubRegistry:
    """假工具注册表 — 供 AgentRunner 读 config.tools。"""

    def get_definitions(self) -> list[Any]:
        return [SimpleNamespace(name="search"), SimpleNamespace(name="mcp__weather")]


class _StubRouter:
    def __init__(self) -> None:
        self.registry = _StubRegistry()


class _StubLoop:
    """固定输出的假 AgentLoop — 匹配 AgentRunner.wrap 读取的元数据接口。"""

    model = "stub-model"
    max_steps = 5
    profile = None
    system_prompt_text = "You are a stub agent for E2E testing."
    system_prompt_blocks: list[Any] = []

    def __init__(self) -> None:
        self.router = _StubRouter()

    def load_messages(self, messages: list[Any]) -> None:
        """noop — 支持 transcript 恢复路径。"""

    async def run(self, user_message: str, *, resume: bool = False) -> AsyncGenerator[LoopEvent, None]:
        for event in _STUB_EVENTS:
            yield event


class StubAgentFactory:
    """E2E 用工厂 — create_loop 返回固定输出 stub loop。"""

    def create_loop(self, working_dir: str | None = None, agent_name: str | None = None) -> _StubLoop:
        return _StubLoop()
