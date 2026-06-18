"""RecordingSubscriber — 订阅 EventBus，把 VizEvent 按 session_id 落盘 jsonl（回放种子）。"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from agent_framework.viz.event_bus import EventBus

logger = logging.getLogger(__name__)


class RecordingSubscriber:
    """订阅 EventBus，按 session_id 把事件 append 到 {storage_dir}/{session_id}.jsonl。

    落盘失败只 log，绝不阻塞事件流或影响 WS 推送。
    """

    def __init__(self, bus: EventBus, storage_dir: Path) -> None:
        self._bus = bus
        self._storage_dir = storage_dir
        self._queue: asyncio.Queue[dict[str, Any]] | None = None
        self._task: asyncio.Task[None] | None = None  # type: ignore[type-arg]

    async def start(self) -> None:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._queue = await self._bus.subscribe()
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        assert self._queue is not None
        try:
            while True:
                event = await self._queue.get()
                self._append(event)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("RecordingSubscriber crashed (event stream unaffected)")

    def _append(self, event: dict[str, Any]) -> None:
        sid = event.get("session_id") or "unknown"
        # 防路径遍历：session_id 应为 32 位 hex，只允许字母数字
        safe_sid = "".join(c for c in str(sid) if c.isalnum()) or "unknown"
        path = self._storage_dir / f"{safe_sid}.jsonl"
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            logger.warning("Failed to record viz event for session %s", safe_sid)

    async def stop(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
