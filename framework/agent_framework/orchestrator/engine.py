"""OrchestratorEngine — 编排引擎，根据任务复杂度路由到合适的 Agent 类型。

复杂度评估使用纯字符数阈值（默认 200），不额外调用 LLM。
简单任务路由到 AgentLoop，复杂任务路由到 PlanAndSolveAgent。
通过 agent_factory 模式创建 Agent 实例，每个 OrchestratorEngine 最多创建 3 个 Agent。
"""

from __future__ import annotations

from typing import AsyncGenerator, Literal

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


class OrchestratorEngine(Agent):
    """编排引擎：评估任务复杂度并路由到合适的 Agent。"""

    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        complexity_threshold: int = 200,
        max_steps_per_plan_item: int = 10,
        max_replans: int = 2,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self._complexity_threshold = complexity_threshold
        self.max_steps_per_plan_item = max_steps_per_plan_item
        self.max_replans = max_replans
        self._agent_count: int = 0

    def _assess_complexity(self, task: str) -> Literal["simple", "complex"]:
        """评估任务复杂度：纯字符数阈值，不调用 LLM。"""
        return "complex" if len(task) > self._complexity_threshold else "simple"

    def _create_agent(self, task: str) -> Agent | None:
        """工厂方法：根据复杂度创建 Agent 实例。超过上限返回 None。"""
        from agent_framework.agents.agent_loop import AgentLoop
        from agent_framework.agents.plan_and_solve import PlanAndSolveAgent

        if self._agent_count >= 3:
            return None

        complexity = self._assess_complexity(task)
        if complexity == "complex":
            agent: Agent = PlanAndSolveAgent(
                adapter=self.adapter,
                model=self.model,
                router=self.router,
                ctx=self.ctx,
                max_steps_per_plan_item=self.max_steps_per_plan_item,
                max_replans=self.max_replans,
            )
        else:
            agent = AgentLoop(
                adapter=self.adapter,
                model=self.model,
                router=self.router,
                ctx=self.ctx,
                max_steps=self.max_steps_per_plan_item,
            )

        self._agent_count += 1
        return agent

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """执行编排流程：评估复杂度 -> 创建 Agent -> 转发事件。"""
        complexity = self._assess_complexity(user_message)
        yield AgentEvent(
            type="step",
            step=0,
            data={
                "complexity": complexity,
                "task_length": len(user_message),
            },
        )

        if self._agent_count >= 3:
            yield AgentEvent(
                type="error",
                step=0,
                data={"error": "Agent 实例数已达上限 3"},
            )
            return

        agent = self._create_agent(user_message)
        if agent is None:
            yield AgentEvent(
                type="error",
                step=0,
                data={"error": "Agent 实例数已达上限 3"},
            )
            return

        step_offset = 1
        async for event in agent.run(user_message):
            yield AgentEvent(
                type=event.type,
                step=event.step + step_offset,
                data=event.data,
            )
