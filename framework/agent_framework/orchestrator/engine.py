"""OrchestratorEngine — 编排引擎，根据任务复杂度路由到合适的 Agent 类型。

三级退化链：
1. 简单任务 → AgentLoop
2. 复杂任务 + 有 Workers → Decomposer → DAGExecutor → 合成
3. 复杂任务 + 无 Workers → PlanAndSolveAgent

通过 worker_registry 参数启用 Worker 管道，支持自动退化。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, Literal

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.llm.base import ILLMAdapter
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

if TYPE_CHECKING:
    from agent_framework.orchestrator.worker_registry import WorkerRegistry


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
        """评估任务复杂度：纯字符数阈值，不调用 LLM。"""
        return "complex" if len(task) > self._complexity_threshold else "simple"

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """执行编排流程：评估复杂度 → 路由到合适的执行路径。"""
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
        from agent_framework.orchestrator.executor import DAGExecutor

        # Step 1: Decompose
        yield AgentEvent(
            type="decompose_start",
            step=1,
            data={"task_length": len(user_message)},
        )

        decomposer = Decomposer(self.adapter, model=self.model)
        try:
            plan = await decomposer.decompose(user_message, self._worker_registry)
        except Exception as exc:
            # Auto-degrade: decompose failed, fall back to PlanAndSolve
            async for event in self._run_plan_and_solve(user_message):
                yield event
            return

        yield AgentEvent(
            type="decompose_done",
            step=1,
            data={"subtask_count": len(plan)},
        )

        # Step 2: Execute via DAGExecutor
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
            if event.type == "orchestrator_error":
                return
            if event.type == "worker_done":
                results.append(event.data)

        # Step 3: Synthesize
        combined = self._synthesize(user_message, results)
        yield AgentEvent(
            type="orchestrator_done",
            step=1,
            data={"synthesized_output": combined},
        )

    def _synthesize(self, user_message: str, results: list[dict]) -> str:
        """合成 Worker 输出：拼接非空 output。"""
        outputs = [r["output"] for r in results if r.get("output")]
        return "\n\n".join(outputs)
