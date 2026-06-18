"""Agent ABC + AgentEvent 测试。"""

from __future__ import annotations

import pytest

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.agent_loop import AgentLoop, LoopEvent


class TestAgentEvent:
    """AgentEvent dataclass 基础测试。"""

    def test_default_data(self) -> None:
        """AgentEvent 默认 data 为空 dict。"""
        event = AgentEvent(type="step", step=1)
        assert event.data == {}

    def test_custom_data(self) -> None:
        """AgentEvent 自定义 data 正确传递。"""
        event = AgentEvent(type="done", step=2, data={"text": "ok"})
        assert event.type == "done"
        assert event.step == 2
        assert event.data == {"text": "ok"}

    def test_all_event_types(self) -> None:
        """AgentEvent type 字段可以接受各种事件类型。"""
        for event_type in ("step", "tool_result", "done", "max_steps", "error"):
            event = AgentEvent(type=event_type, step=0)
            assert event.type == event_type


class TestAgentABC:
    """Agent 抽象基类测试。"""

    def test_cannot_instantiate(self) -> None:
        """Agent ABC 不可直接实例化。"""
        with pytest.raises(TypeError):
            Agent()  # type: ignore[abstract]

    def test_subclass_can_instantiate(self) -> None:
        """实现 run() 的 Agent 子类可以实例化。"""

        class SimpleAgent(Agent):
            async def run(self, user_message: str):
                yield AgentEvent(type="done", step=1)  # type: ignore[misc]

        agent = SimpleAgent()
        assert isinstance(agent, Agent)

    def test_agent_loop_is_agent(self) -> None:
        """AgentLoop 是 Agent 的子类。"""
        assert issubclass(AgentLoop, Agent)

    def test_loop_event_is_agent_event(self) -> None:
        """LoopEvent 是 AgentEvent 的子类。"""
        assert issubclass(LoopEvent, AgentEvent)
