"""Agent 工厂 — 组装 AgentLoop 实例。"""

from __future__ import annotations

from pathlib import Path

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.llm import create_adapter
from agent_framework.llm.resilient import ResilientLLMAdapter
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

from app.config import Settings


class AgentFactory:
    """根据配置创建 AgentLoop 实例，复用无状态组件。"""

    def __init__(self, adapter: ResilientLLMAdapter, model: str, storage_dir: Path | None = None) -> None:
        self._adapter = adapter
        self._model = model
        self._router = ToolRouter(create_builtin_registry())
        self._storage_dir = storage_dir

    @classmethod
    def from_settings(cls, settings: Settings, storage_dir: Path | None = None) -> AgentFactory:
        adapter = create_adapter(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
        return cls(adapter=adapter, model=settings.llm_model, storage_dir=storage_dir)

    def create_loop(self) -> AgentLoop:
        ctx = ToolUseContext()
        if self._storage_dir is not None:
            ctx.working_dir = str(self._storage_dir / "shared_workspace")
        return AgentLoop(
            adapter=self._adapter,
            model=self._model,
            router=self._router,
            ctx=ctx,
        )
