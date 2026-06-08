"""WorkerManager — Worker 生命周期管理：创建、执行、消息、状态查询。"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from agent_framework.agents.base import AgentEvent
from agent_framework.orchestrator.models import WorkerHandle

if TYPE_CHECKING:
    from agent_framework.agents.base import Agent
    from agent_framework.llm.base import ILLMAdapter
    from agent_framework.orchestrator.worker_registry import WorkerRegistry
    from agent_framework.tools.router import ToolRouter
    from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)


def _new_worker_id() -> str:
    return f"w_{uuid.uuid4().hex[:8]}"


async def _collect_output(agent: Agent, prompt: str) -> str:
    """从 agent.run() 收集文本输出。"""
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
            raise RuntimeError((event.data or {}).get("error", "Worker error"))
    return text or ""


class WorkerManager:
    """管理 Worker 的创建、执行和状态跟踪。"""

    def __init__(
        self,
        registry: WorkerRegistry,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
    ) -> None:
        self._registry = registry
        self._adapter = adapter
        self._model = model
        self._router = router
        self._ctx = ctx
        self._workers: list[WorkerHandle] = []

    async def spawn(self, worker_name: str, prompt: str) -> WorkerHandle:
        """创建并执行一个 Worker，返回执行结果。"""
        spec = self._registry.get(worker_name)
        worker_id = _new_worker_id()
        handle = WorkerHandle(id=worker_id, worker_name=worker_name, status="running")
        self._workers.append(handle)
        try:
            agent = spec.factory(
                adapter=self._adapter,
                model=self._model,
                router=self._router,
                ctx=self._ctx,
            )
            output = await _collect_output(agent, prompt)
            completed = WorkerHandle(
                id=worker_id, worker_name=worker_name, status="completed", output=output,
            )
            self._workers[-1] = completed
            return completed
        except Exception as e:
            logger.error("Worker '%s' failed: %s", worker_name, e)
            failed = WorkerHandle(
                id=worker_id, worker_name=worker_name, status="failed", error=str(e),
            )
            self._workers[-1] = failed
            return failed

    def list_workers(self, *, status: str = "all") -> list[WorkerHandle]:
        """查询 Worker 列表，可按状态过滤。"""
        if status == "all":
            return list(self._workers)
        return [w for w in self._workers if w.status == status]

    async def send_message(self, worker_id: str, message: str) -> WorkerHandle:
        """向已完成的 Worker 发送追加消息（继续执行）。"""
        original = next((w for w in self._workers if w.id == worker_id), None)
        if original is None:
            raise KeyError(f"Worker not found: {worker_id}")

        followup_prompt = (
            f"[前一轮输出]\n{original.output}\n\n"
            f"[追加指令]\n{message}"
        )
        return await self.spawn(original.worker_name, followup_prompt)
