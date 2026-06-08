"""DAGExecutor — 将 SubTask 通过注册的 Worker 串行执行（P1）。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncGenerator

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.orchestrator.models import SubTask, SubTaskResult

if TYPE_CHECKING:
    from agent_framework.llm.base import ILLMAdapter
    from agent_framework.orchestrator.worker_registry import WorkerRegistry
    from agent_framework.tools.router import ToolRouter
    from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)


class DAGExecutor:
    """将 SubTask 计划通过 Worker 串行执行。

    P1 使用串行执行；P2 将替换为并行执行（保持相同接口）。

    每个 subtask 的执行流程：
    1. yield worker_start 事件
    2. 通过 factory 创建 agent
    3. 收集 agent 输出
    4. yield worker_done 事件
    遇到异常时 yield orchestrator_error 并快速返回。
    """

    def __init__(
        self,
        worker_registry: WorkerRegistry,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
    ) -> None:
        self._registry = worker_registry
        self._adapter = adapter
        self._model = model
        self._router = router
        self._ctx = ctx

    async def execute(self, plan: list[SubTask]) -> AsyncGenerator[AgentEvent, None]:
        """串行执行计划中的所有 SubTask。"""
        self._validate_order(plan)
        for subtask in plan:
            yield AgentEvent(
                type="worker_start",
                step=1,
                data={
                    "subtask_id": subtask.id,
                    "worker": subtask.worker,
                    "prompt": subtask.prompt,
                },
            )
            result = await self._run_worker(subtask)
            yield AgentEvent(
                type="worker_done",
                step=1,
                data={
                    "subtask_id": result.id,
                    "worker": result.worker,
                    "output": result.output,
                    "success": result.success,
                    "error": result.error,
                },
            )
            if not result.success:
                yield AgentEvent(
                    type="orchestrator_error",
                    step=1,
                    data={
                        "error": f"Worker '{result.worker}' failed: {result.error}",
                        "subtask_id": result.id,
                    },
                )
                return

    def _validate_order(self, plan: list[SubTask]) -> None:
        """验证 plan 是否按拓扑序排列：每个 subtask 的 depends_on 必须在它之前出现。"""
        seen: set[str] = set()
        for subtask in plan:
            for dep in subtask.depends_on:
                if dep not in seen:
                    raise ValueError(
                        f"Plan not in topological order: subtask '{subtask.id}' "
                        f"depends on '{dep}' which hasn't been executed yet"
                    )
            seen.add(subtask.id)

    async def _run_worker(self, subtask: SubTask) -> SubTaskResult:
        """执行单个 subtask，捕获异常。"""
        spec = self._registry.get(subtask.worker)
        try:
            agent = spec.factory(
                adapter=self._adapter,
                model=self._model,
                router=self._router,
                ctx=self._ctx,
            )
            output = await self._collect_output(agent, subtask.prompt)
            return SubTaskResult(
                id=subtask.id, worker=subtask.worker, output=output, success=True,
            )
        except Exception as e:
            logger.error("Worker '%s' failed: %s", subtask.worker, e)
            return SubTaskResult(
                id=subtask.id, worker=subtask.worker, output="", success=False, error="Worker execution failed",
            )

    async def _collect_output(self, agent: Agent, prompt: str) -> str:
        """从 agent.run() 中收集文本输出。error 事件抛 RuntimeError。"""
        text = ""
        async for event in agent.run(prompt):
            if event.type == "done":
                content = (event.data or {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text_value = block.get("text", "")
                        if isinstance(text_value, str):
                            text += text_value
            elif event.type == "error":
                raise RuntimeError((event.data or {}).get("error", "Unknown worker error"))
        return text or ""
