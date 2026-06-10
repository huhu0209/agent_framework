"""TaskRunner — 后台异步执行 AgentLoop。"""

from __future__ import annotations

import asyncio
import logging

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.llm.base import ILLMAdapter
from agent_framework.tasks.manager import TaskManager
from agent_framework.tasks.types import RuntimeTask, RuntimeTaskStatus, TaskStatus
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)


class TaskRunner:
    """后台任务执行器。asyncio.Queue 通知主循环。"""

    def __init__(
        self,
        task_manager: TaskManager,
        adapter: ILLMAdapter,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        *,
        max_concurrent: int = 3,
        timeout_seconds: float = 300.0,
    ):
        self._task_manager = task_manager
        self._adapter = adapter
        self._model = model
        self._router = router
        self._ctx = ctx
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout_seconds
        self._notifications: asyncio.Queue[RuntimeTask] = asyncio.Queue()
        self._running: dict[str, asyncio.Task] = {}

    async def run(self, task_id: str, prompt: str):
        """启动后台执行，立即返回。"""
        if task_id in self._running:
            logger.warning("任务 %s 已在运行中，跳过重复启动", task_id)
            return
        rt = RuntimeTask(task_id=task_id, prompt=prompt)
        await self._task_manager.update(task_id, status=TaskStatus.IN_PROGRESS)
        atask = asyncio.create_task(self._execute(rt))
        self._running[task_id] = atask

    async def _execute(self, rt: RuntimeTask):
        async with self._semaphore:
            try:
                loop = AgentLoop(
                    adapter=self._adapter,
                    model=self._model,
                    router=self._router,
                    ctx=self._ctx,
                    max_steps=30,
                )

                async def _run_loop():
                    async for event in loop.run(rt.prompt):
                        if event.type == "done":
                            rt.status = RuntimeTaskStatus.COMPLETED
                            rt.output = event.data.get("content", "")
                            await self._task_manager.update(
                                rt.task_id,
                                status=TaskStatus.COMPLETED,
                                description=f"输出: {rt.output[:500]}",
                            )
                        elif event.type == "error":
                            rt.status = RuntimeTaskStatus.ERROR
                            rt.error = event.data.get("error", "")
                            await self._task_manager.update(
                                rt.task_id,
                                status=TaskStatus.FAILED,
                                description=f"错误: {rt.error[:500]}",
                            )

                await asyncio.wait_for(_run_loop(), timeout=self._timeout)

            except asyncio.TimeoutError:
                rt.status = RuntimeTaskStatus.TIMEOUT
                rt.error = f"任务超时 ({self._timeout}s)"
                try:
                    await self._task_manager.update(
                        rt.task_id,
                        status=TaskStatus.FAILED,
                        description=f"超时: {rt.error}",
                    )
                except Exception:
                    logger.debug("任务超时状态更新失败: %s", rt.task_id)
            except Exception as exc:
                rt.status = RuntimeTaskStatus.ERROR
                rt.error = str(exc)
                try:
                    await self._task_manager.update(
                        rt.task_id,
                        status=TaskStatus.FAILED,
                        description=f"异常: {str(exc)[:500]}",
                    )
                except Exception:
                    logger.debug("任务异常状态更新失败: %s", rt.task_id)
            finally:
                self._notifications.put_nowait(rt)
                self._running.pop(rt.task_id, None)

    async def drain_notifications(self) -> list[RuntimeTask]:
        """主循环每轮调用：取出所有已完成的通知。"""
        results = []
        while True:
            try:
                results.append(self._notifications.get_nowait())
            except asyncio.QueueEmpty:
                break
        return results
