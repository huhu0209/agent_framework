"""OrchestratorEngine — 编排引擎，根据任务复杂度路由到合适的 Agent 类型。

三级退化链：
1. 简单任务 → AgentLoop
2. 复杂任务 + 有 Workers → Decomposer → DAGExecutor → 合成
3. 复杂任务 + 无 Workers → PlanAndSolveAgent

通过 worker_registry 参数启用 Worker 管道，支持自动退化。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncGenerator, Literal

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.orchestrator.models import SubTask, OrchestratorEventType
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

if TYPE_CHECKING:
    from agent_framework.orchestrator.worker_registry import WorkerRegistry

logger = logging.getLogger(__name__)

_MAX_USER_MESSAGE_LENGTH = 100_000


class OrchestratorEngine(Agent):
    """编排引擎：评估任务复杂度并路由到合适的 Agent。

    继承 Agent 基类以保持多态兼容性——调用者可以统一处理
    AgentLoop、PlanAndSolveAgent 和 OrchestratorEngine 实例。
    """

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
        worker_registry: WorkerRegistry | None = None,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self._complexity_threshold = complexity_threshold
        self.max_steps_per_plan_item = max_steps_per_plan_item
        self.max_replans = max_replans
        self._worker_registry = worker_registry

    def _assess_complexity(self, task: str) -> Literal["simple", "complex"]:
        """评估任务复杂度：纯字符数阈值，不调用 LLM。

        Design tradeoff: 字符数阈值简单快速，但存在误判——
        附带大量上下文的简单任务可能被标为 complex，
        而简短但语义复杂的请求可能被标为 simple。
        当前阶段优先零延迟、零成本；未来可引入关键词或 LLM 辅助判断。
        """
        return "complex" if len(task.strip()) > self._complexity_threshold else "simple"

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """执行编排流程：评估复杂度 → 路由到合适的执行路径。"""
        if len(user_message) > _MAX_USER_MESSAGE_LENGTH:
            raise ValueError(
                f"User message too long: {len(user_message)} chars "
                f"(max {_MAX_USER_MESSAGE_LENGTH})"
            )
        complexity = self._assess_complexity(user_message)
        yield AgentEvent(
            type="step",
            step=0,
            data={
                "complexity": complexity,
                "task_length": len(user_message),
            },
        )

        if complexity == "simple":
            async for event in self._run_simple(user_message):
                yield event
            return

        # Complex task
        if self._worker_registry and self._worker_registry.has_workers():
            async for event in self._run_orchestrated(user_message):
                yield event
        else:
            async for event in self._run_plan_and_solve(user_message):
                yield event

    async def _run_simple(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """简单任务路径：创建 AgentLoop，转发事件。"""
        from agent_framework.agents.agent_loop import AgentLoop

        agent = AgentLoop(
            adapter=self.adapter,
            model=self.model,
            router=self.router,
            ctx=self.ctx,
            max_steps=self.max_steps_per_plan_item,
        )
        step_offset = 1
        async for event in agent.run(user_message):
            yield AgentEvent(
                type=event.type,
                step=event.step + step_offset,
                data=event.data,
            )

    async def _run_plan_and_solve(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """复杂任务路径（无 Workers）：创建 PlanAndSolveAgent，转发事件。"""
        from agent_framework.agents.plan_and_solve import PlanAndSolveAgent

        agent = PlanAndSolveAgent(
            adapter=self.adapter,
            model=self.model,
            router=self.router,
            ctx=self.ctx,
            max_steps_per_plan_item=self.max_steps_per_plan_item,
            max_replans=self.max_replans,
        )
        step_offset = 1
        async for event in agent.run(user_message):
            yield AgentEvent(
                type=event.type,
                step=event.step + step_offset,
                data=event.data,
            )

    async def _run_orchestrated(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """复杂任务路径（有 Workers）：Decomposer → DAGExecutor → 合成。"""
        from agent_framework.orchestrator.decomposer import Decomposer

        yield AgentEvent(
            type=OrchestratorEventType.DECOMPOSE_START,
            step=1,
            data={"task_length": len(user_message)},
        )

        decomposer = Decomposer(self.adapter, model=self.model)
        try:
            plan = await decomposer.decompose(user_message, self._worker_registry)
        except Exception as exc:
            logger.warning("Decompose failed, degrading to PlanAndSolve: %s", exc)
            yield AgentEvent(
                type=OrchestratorEventType.DEGRADE,
                step=1,
                data={"reason": "Decomposition failed"},
            )
            async for event in self._run_plan_and_solve(user_message):
                yield event
            return

        yield AgentEvent(
            type=OrchestratorEventType.DECOMPOSE_DONE,
            step=1,
            data={"subtask_count": len(plan)},
        )

        async for event in self._execute_plan(plan):
            yield event

    async def _execute_plan(self, plan: list[SubTask]) -> AsyncGenerator[AgentEvent, None]:
        """执行子任务计划并合成结果。"""
        from agent_framework.orchestrator.executor import DAGExecutor

        executor = DAGExecutor(
            self._worker_registry,
            self.adapter,
            model=self.model,
            router=self.router,
            ctx=self.ctx,
        )
        results: list[dict] = []
        async for event in executor.execute(plan):
            yield event
            if event.type == OrchestratorEventType.ORCHESTRATOR_ERROR:
                return
            if event.type == OrchestratorEventType.WORKER_DONE:
                results.append(event.data)

        combined = self._synthesize("", results)
        yield AgentEvent(
            type=OrchestratorEventType.ORCHESTRATOR_DONE,
            step=1,
            data={"synthesized_output": combined},
        )

    def _synthesize(self, user_message: str, results: list[dict]) -> str:
        """合成 Worker 输出：拼接非空 output，附带 Worker 标识以便溯源。"""
        parts = []
        for r in results:
            output = r.get("output")
            if output:
                worker = r.get("worker", "unknown")
                parts.append(f"[{worker}]\n{output}")
        return "\n\n".join(parts)
