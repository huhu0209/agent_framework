"""Session 管理 — 内存存储，含 TTL 淘汰。"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

from agent_framework.agents.agent_loop import AgentLoop

logger = logging.getLogger(__name__)

SESSION_TTL = 3600  # 1 hour


@dataclass
class ChatSession:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    agent_loop: AgentLoop | None = None
    task: asyncio.Task | None = None  # type: ignore[type-arg]
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """管理活跃 session 的生命周期，含 TTL 自动淘汰。"""

    def __init__(self, ttl: float = SESSION_TTL) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._ttl = ttl
        self._cleanup_task: asyncio.Task | None = None  # type: ignore[type-arg]

    def start_cleanup(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

    def create(self, agent_loop: AgentLoop) -> ChatSession:
        sid = uuid.uuid4().hex
        session = ChatSession(session_id=sid, agent_loop=agent_loop)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> ChatSession | None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.created_at = time.time()
        return session

    def remove(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session and session.task and not session.task.done():
            session.task.cancel()

    def cancel_all(self) -> None:
        for session in self._sessions.values():
            if session.task and not session.task.done():
                session.task.cancel()
        self._sessions.clear()

    def replace_task(self, session: ChatSession, new_task: asyncio.Task) -> None:  # type: ignore[type-arg]
        if session.task and not session.task.done():
            session.task.cancel()
        session.task = new_task

    async def _cleanup_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(60)
                self._evict_expired()
        except asyncio.CancelledError:
            pass

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.created_at > self._ttl
        ]
        for sid in expired:
            self.remove(sid)
            logger.info("Evicted expired session %s", sid)
