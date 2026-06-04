"""Agent 工厂 — 组装 AgentLoop 实例。"""

from __future__ import annotations

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.llm import create_adapter
from agent_framework.llm.resilient import ResilientLLMAdapter
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

from app.config import Settings


class AgentFactory:
    """根据配置创建 AgentLoop 实例，复用无状态组件。"""

    def __init__(self, adapter: ResilientLLMAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model
        self._router = ToolRouter(create_builtin_registry())
        self._ctx = ToolUseContext()

    @classmethod
    def from_settings(cls, settings: Settings) -> AgentFactory:
        adapter = create_adapter(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
        return cls(adapter=adapter, model=settings.llm_model)

    def create_loop(self) -> AgentLoop:
        return AgentLoop(
            adapter=self._adapter,
            model=self._model,
            router=self._router,
            ctx=self._ctx,
        )
