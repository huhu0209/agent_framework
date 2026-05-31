"""EventBus — 基于 asyncio.Queue 的 pub-sub 事件总线。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """异步事件总线，支持 subscribe/publish/unsubscribe。

    subscribe() 返回有界 asyncio.Queue，消费方 await queue.get()。
    publish() 广播到所有订阅者，满队列丢弃最旧事件。
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
        self._maxsize = maxsize

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """订阅事件，返回一个有界 Queue。"""
        async with self._lock:
            q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._maxsize)
            self._subscribers.add(q)
            return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """取消订阅，Queue 不再收到新事件。"""
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        """广播事件到所有订阅者。满队列丢弃最旧后推入。"""
        async with self._lock:
            snapshot = list(self._subscribers)

        for q in snapshot:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(event)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
