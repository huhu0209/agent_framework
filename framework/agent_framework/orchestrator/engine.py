"""OrchestratorEngine — 协调者 Agent Loop，LLM 自路由编排。

设计理念：
- 协调者是一个 AgentLoop，只拥有编排工具（spawn_worker / send_message / list_workers）
- LLM 自己理解任务，决定何时派生 Worker、何时综合结果
- Worker 通过 WorkerRegistry.factory 创建，执行结果返回给 LLM
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncGenerator

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

if TYPE_CHECKING:
    from agent_framework.orchestrator.worker_registry import WorkerRegistry

logger = logging.getLogger(__name__)

_MAX_USER_MESSAGE_LENGTH = 100_000


class OrchestratorEngine(Agent):
    """协调者 Agent Loop：LLM 自路由编排引擎。"""

    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        worker_registry: WorkerRegistry,
        max_steps: int = 20,
    ) -> None:
        super().__init__()
        if worker_registry is None:
            raise ValueError("worker_registry is required for OrchestratorEngine")
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self._worker_registry = worker_registry
        self._max_steps = max_steps

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """启动协调者 Agent Loop 处理用户任务。"""
        if len(user_message) > _MAX_USER_MESSAGE_LENGTH:
            raise ValueError(
                f"User message too long: {len(user_message)} chars "
                f"(max {_MAX_USER_MESSAGE_LENGTH})"
            )

        # Lazy imports — 避免 agents ↔ orchestrator 循环依赖
        from agent_framework.agents.agent_loop import AgentLoop
        from agent_framework.orchestrator.coordinator_prompt import build_coordinator_prompt
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        from agent_framework.orchestrator.worker_agent import WorkerManager
        from agent_framework.tools.registry import ToolRegistry

        # 创建 WorkerManager
        worker_manager = WorkerManager(
            self._worker_registry,
            self.adapter,
            model=self.model,
            router=self.router,
            ctx=self.ctx,
        )

        # 创建协调者工具注册表
        tool_specs = create_coordinator_tools(worker_manager)
        coord_registry = ToolRegistry()
        for spec in tool_specs:
            coord_registry.register(spec)

        # 创建协调者的 ToolRouter（从主 router 派生，使用协调者专属 registry）
        coord_router = self.router.derive(coord_registry)

        # 构建协调者上下文（注入 worker_manager）
        coord_ctx = ToolUseContext(
            working_dir=self.ctx.working_dir,
            message_history=list(self.ctx.message_history),
            mcp_clients=dict(self.ctx.mcp_clients),
            app_state=dict(self.ctx.app_state),
            extra={**self.ctx.extra, "worker_manager": worker_manager},
        )

        # 构建 system prompt
        system_prompt = build_coordinator_prompt(self._worker_registry)

        # 创建并运行协调者 AgentLoop
        coordinator = AgentLoop(
            adapter=self.adapter,
            model=self.model,
            router=coord_router,
            ctx=coord_ctx,
            max_steps=self._max_steps,
            system_prompt=system_prompt,
        )

        async for event in coordinator.run(user_message):
            yield event
