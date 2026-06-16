"""WorkerManager — Worker 生命周期管理：创建、执行、消息、状态查询。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import OrderedDict
from typing import TYPE_CHECKING

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


# E2: 同时存活的 worker agent 上限（LRU 淘汰最旧，防内存泄漏）
_MAX_LIVE_AGENTS = 8

# H-E3: worker 整体执行超时（秒）。单工具调用仍由 ToolSpec.timeout_ms 兜底，此处兜多步循环。
_DEFAULT_TIMEOUT = 300


async def _collect_output(agent: Agent, prompt: str, *, resume: bool = False) -> str:
    """从 agent.run() 收集文本输出。

    E2: resume=True 时调 agent.run(prompt, resume=True)（AgentLoop 继承 _messages 历史）。
    Agent ABC 的 run 签名不含 resume kwarg，运行时 AgentLoop.run 支持。
    """
    text = ""
    if resume:
        events = agent.run(prompt, resume=True)  # type: ignore[call-arg]
    else:
        events = agent.run(prompt)
    async for event in events:
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
        self._workers: dict[str, WorkerHandle] = {}
        # E2: 保留 agent 实例供 send_message resume，LRU 上限 _MAX_LIVE_AGENTS
        self._agents: OrderedDict[str, Agent] = OrderedDict()

    async def spawn(self, worker_name: str, prompt: str) -> WorkerHandle:
        """创建并执行一个 Worker，返回执行结果。"""
        spec = self._registry.get(worker_name)
        worker_id = _new_worker_id()
        self._workers[worker_id] = WorkerHandle(id=worker_id, worker_name=worker_name, status="running")
        try:
            # E2: 隔离 ctx，防多存活 worker agent 共享 ctx 互相覆盖 planning_session
            isolated_ctx = self._ctx.model_copy(update={"extra": dict(self._ctx.extra)})
            agent = spec.factory(
                adapter=self._adapter,
                model=self._model,
                router=self._router,
                ctx=isolated_ctx,
            )
            try:
                output = await asyncio.wait_for(
                    _collect_output(agent, prompt), timeout=_DEFAULT_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Worker '{worker_name}' 执行超时（{_DEFAULT_TIMEOUT}s）")
            self._retain_agent(worker_id, agent)  # E2: 保留供 send_message resume
            completed = WorkerHandle(
                id=worker_id, worker_name=worker_name, status="completed", output=output,
            )
            self._workers[worker_id] = completed
            return completed
        except Exception as e:
            logger.error("Worker '%s' failed: %s", worker_name, e)
            failed = WorkerHandle(
                id=worker_id, worker_name=worker_name, status="failed", error=str(e),
            )
            self._workers[worker_id] = failed
            return failed

    def _retain_agent(self, worker_id: str, agent: Agent) -> None:
        """E2: 保留 agent 供 resume，LRU 淘汰最旧。"""
        self._agents[worker_id] = agent
        self._agents.move_to_end(worker_id)
        while len(self._agents) > _MAX_LIVE_AGENTS:
            evicted_id, _ = self._agents.popitem(last=False)
            logger.warning("Worker agent %s 被 LRU 淘汰，后续 send_message 将报错", evicted_id)

    def list_workers(self, *, status: str = "all") -> list[WorkerHandle]:
        """查询 Worker 列表，可按状态过滤。"""
        workers = list(self._workers.values())
        if status == "all":
            return workers
        return [w for w in workers if w.status == status]

    async def send_message(self, worker_id: str, message: str) -> WorkerHandle:
        """向已完成的 Worker 发送追加消息，在原 agent 上 resume（继承历史）。"""
        original = self._workers.get(worker_id)
        if original is None:
            raise KeyError(f"Worker not found: {worker_id}")

        agent = self._agents.get(worker_id)
        if agent is None:
            raise RuntimeError(f"Worker {worker_id} 已被回收，需重新 spawn")
        self._agents.move_to_end(worker_id)  # LRU: 标记最近使用

        try:
            output = await _collect_output(agent, message, resume=True)
            completed = WorkerHandle(
                id=worker_id, worker_name=original.worker_name, status="completed", output=output,
            )
            self._workers[worker_id] = completed
            return completed
        except Exception as e:
            logger.error("Worker '%s' resume failed: %s", worker_id, e)
            failed = WorkerHandle(
                id=worker_id, worker_name=original.worker_name, status="failed", error=str(e),
            )
            self._workers[worker_id] = failed
            return failed
