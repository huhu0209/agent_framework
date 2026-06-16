"""TeamManager — 管理持久化队友。"""

from __future__ import annotations

import asyncio
import logging
import time

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.agents.sub_agent import create_filtered_router
from agent_framework.llm.base import ILLMAdapter
from agent_framework.teams.bus import MessageBus
from agent_framework.teams.types import TeamNotification, TeammateConfig, TeammateStatus
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)


class TeamManager:
    """管理持久化队友进程。

    H-G5 并发约束（重要）：本类设计为 **单线程 asyncio 串行使用**，不加锁：
    - 各队友 ``_loop`` 协程只写自己的 ``_statuses[config.name]`` key，互不交叉；
    - ``_configs``/``_tasks``/初始 ``_statuses`` 仅在 ``spawn()``（lead 单线程调用）阶段写入；
    - ``list_all()`` 遍历的 key 集合在 spawn 阶段固定，迭代期间不增删。

    Python asyncio 单线程 + dict 原子操作 + 各写各的 key → 无实际竞态。
    若未来引入多线程或将 ``_loop`` 改为多进程，须重新评估并加锁。
    """

    def __init__(
        self,
        team_dir,
        bus: MessageBus,
        adapter: ILLMAdapter,
        router: ToolRouter,
        ctx: ToolUseContext,
    ):
        self._dir = team_dir
        self._bus = bus
        self._adapter = adapter
        self._router = router
        self._ctx = ctx
        self._configs: dict[str, TeammateConfig] = {}
        self._statuses: dict[str, TeammateStatus] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self.notifications: asyncio.Queue[TeamNotification] = asyncio.Queue()

    async def spawn(self, config: TeammateConfig) -> None:
        """创建并启动一个队友循环。"""
        self._configs[config.name] = config
        self._statuses[config.name] = TeammateStatus.IDLE
        atask = asyncio.create_task(self._loop(config))
        self._tasks[config.name] = atask

    async def shutdown(self, name: str) -> None:
        """请求关闭指定队友。"""
        self._bus.send("lead", name, "请关闭", msg_type="shutdown_request")

    def list_all(self) -> str:
        """返回所有队友的状态面板。"""
        if not self._configs:
            return "(无队友)"
        lines = []
        for name, config in self._configs.items():
            status = self._statuses.get(name, TeammateStatus.IDLE)
            lines.append(f"  [{status.value}] {name} ({config.role})")
        return "\n".join(lines)

    async def _loop(self, config: TeammateConfig) -> None:
        """队友持久循环：读收件箱 → 处理 → 等待。"""
        model = config.model or "fake-model"
        filtered = create_filtered_router(self._router, config.allowed_tools)
        ctx = ToolUseContext(
            working_dir=self._ctx.working_dir,
            extra={**self._ctx.extra, "teammate_name": config.name, "message_bus": self._bus},
        )
        loop = AgentLoop(
            adapter=self._adapter,
            model=model,
            router=filtered,
            ctx=ctx,
            max_steps=30,
            system_prompt=config.system_prompt,
        )
        idle_start = time.monotonic()

        while self._statuses[config.name] != TeammateStatus.SHUTDOWN:
            inbox = self._bus.read_inbox(config.name)

            if any(m.type == "shutdown_request" for m in inbox):
                self._statuses[config.name] = TeammateStatus.SHUTDOWN
                break

            if not inbox:
                self._statuses[config.name] = TeammateStatus.IDLE
                if time.monotonic() - idle_start > config.max_idle_seconds:
                    self._statuses[config.name] = TeammateStatus.SHUTDOWN
                    break
                await asyncio.sleep(2)
                continue

            self._statuses[config.name] = TeammateStatus.WORKING
            idle_start = time.monotonic()

            prompt = "\n\n".join(
                f"<inbox from='{m.from_}'>\n{m.content}\n</inbox>"
                for m in inbox
            )

            async for event in loop.run(prompt, resume=True):
                if event.type in ("done", "error", "max_steps"):
                    break

            self._statuses[config.name] = TeammateStatus.IDLE

        self.notifications.put_nowait(
            TeamNotification(name=config.name, status="shutdown")
        )
