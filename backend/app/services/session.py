"""Session 管理 — 内存存储，含 TTL 淘汰，可选持久化。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiofiles

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.transcript import TranscriptWriter

logger = logging.getLogger(__name__)

SESSION_TTL = 3600  # 1 hour

# A2: 与 app.models.SESSION_ID_RE 一致；本地定义避免 services → models 循环依赖
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def _safe_json_loads(line: str, *, source: str) -> dict | None:
    """A4: 容错 JSON 解析。坏行返回 None 并告警，不抛 JSONDecodeError。"""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        logger.warning("Skipping malformed JSON line in %s: %r", source, line[:80])
        return None


@dataclass
class ChatSession:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    agent_loop: AgentLoop | None = None
    task: asyncio.Task | None = None  # type: ignore[type-arg]
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)  # H-A2: 活跃判定，get() 更新
    transcript_writer: TranscriptWriter | None = None


class SessionManager:
    """管理活跃 session 的生命周期，含 TTL 自动淘汰。"""

    def __init__(self, ttl: float = SESSION_TTL, storage_dir: Path | None = None, redis_client: Any | None = None) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._ttl = ttl
        self._storage_dir = storage_dir
        self._redis = redis_client
        self._cleanup_task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._session_list_cache: list[dict] | None = None
        self._history_lock = asyncio.Lock()  # H-A6: 保护 history.jsonl 并发 append

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        """A2: 校验 session_id 为 32 位 hex，防路径遍历。非法则 raise ValueError。"""
        if not isinstance(session_id, str) or not _SESSION_ID_RE.match(session_id):
            raise ValueError(f"invalid session_id: {session_id!r}")

    async def _atomic_write(self, path: Path, content: str) -> None:
        """原子写入：write-to-temp + os.replace，防止崩溃时丢失。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".sess_")
        try:
            os.close(fd)
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
                await f.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def start_cleanup(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

    async def create(self, agent_loop: AgentLoop, *, title: str = "") -> ChatSession:
        sid = uuid.uuid4().hex
        writer = None
        if self._storage_dir:
            transcript_path = self._storage_dir / f"{sid}.jsonl"
            writer = TranscriptWriter(transcript_path)
            await self._append_history(sid, title or "新会话")
        session = ChatSession(session_id=sid, agent_loop=agent_loop, transcript_writer=writer)
        self._sessions[sid] = session
        self._invalidate_list_cache()
        return session

    def get(self, session_id: str) -> ChatSession | None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.last_accessed = time.time()  # H-A2: 更新 last_accessed，不刷新 created_at
        return session

    async def get_messages(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        before: float | None = None,
    ) -> tuple[list[dict], bool, str | None] | None:
        """获取消息，支持分页。返回 (messages, has_more, next_cursor) 或 None。"""
        all_messages = await self._get_all_messages(session_id)
        if all_messages is None:
            return None

        if limit is None:
            return all_messages, False, None

        # 按时间排序（新 → 旧），取最新的 limit+1 条来判断 has_more
        sorted_msgs = sorted(all_messages, key=lambda m: m.get("timestamp", 0), reverse=True)

        if before is not None:
            sorted_msgs = [m for m in sorted_msgs if m.get("timestamp", 0) < before]

        has_more = len(sorted_msgs) > limit
        page = sorted_msgs[:limit]

        # 恢复时间正序（旧 → 新）
        page.reverse()

        next_cursor = None
        if has_more and page:
            next_cursor = str(page[0].get("timestamp", 0))

        return page, has_more, next_cursor

    async def count_messages(self, session_id: str) -> int | None:
        """获取会话消息总数。"""
        all_messages = await self._get_all_messages(session_id)
        if all_messages is None:
            return None
        return len(all_messages)

    async def _get_all_messages(self, session_id: str) -> list[dict] | None:
        """三层查找：内存 → Redis → JSONL。"""
        self._validate_session_id(session_id)  # A2
        # 1. 内存
        session = self._sessions.get(session_id)
        if session is not None:
            return session.messages
        # 2. Redis
        cached = await self._redis_get_messages(session_id)  # H-A1: async
        if cached is not None:
            return cached
        # 3. JSONL 冷读 → 回填 Redis
        if not self._storage_dir:
            return None
        transcript_path = self._storage_dir / f"{session_id}.jsonl"
        if not transcript_path.exists():
            return None
        return await self._cold_read_jsonl(transcript_path, session_id)  # H-A1: _cold_read 已 async

    async def _cold_read_jsonl(self, transcript_path: Path, session_id: str) -> list[dict]:
        """JSONL 冷读 → 回填 Redis。H-A1: 改 async（_redis_set_messages 已 async）。"""
        from agent_framework.transcript import TranscriptReader
        reader = TranscriptReader(transcript_path)
        result: list[dict] = []
        for ev in reader.events():
            if ev.type.value == "user":
                text = ev.content if isinstance(ev.content, str) else ""
                result.append({"role": "user", "content": text, "timestamp": ev.timestamp})
            elif ev.type.value == "assistant":
                blocks = ev.content if isinstance(ev.content, list) else []
                result.append({"role": "agent", "blocks": blocks, "timestamp": ev.timestamp})
            elif ev.type.value == "tool_result":
                continue  # tool_result 不展示在历史中
        await self._redis_set_messages(session_id, result)  # H-A1
        return result

    def remove(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            if session.transcript_writer:
                session.transcript_writer.close()
            if session.task and not session.task.done():
                session.task.cancel()

    def cancel_all(self) -> None:
        for session in self._sessions.values():
            if session.transcript_writer:
                session.transcript_writer.close()
            if session.task and not session.task.done():
                session.task.cancel()
        self._sessions.clear()

    def replace_task(self, session: ChatSession, new_task: asyncio.Task) -> None:  # type: ignore[type-arg]
        if session.task and not session.task.done():
            session.task.cancel()
        session.task = new_task

    async def _append_history(self, session_id: str, title: str) -> None:
        if not self._storage_dir:
            return
        history_path = self._storage_dir / "history.jsonl"
        entry = json.dumps({
            "session_id": session_id,
            "title": title,
            "created_at": time.time(),
        }, ensure_ascii=False)
        async with self._history_lock:  # H-A6: 防并发 append 交错
            history_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(history_path, "a", encoding="utf-8") as f:
                await f.write(entry + "\n")

    async def update_title(self, session_id: str, title: str) -> bool:
        """更新 history.jsonl 中的标题，返回是否实际更新。"""
        if not self._storage_dir:
            return False
        history_path = self._storage_dir / "history.jsonl"
        if not history_path.exists():
            return False
        lines = []
        updated = False
        async with aiofiles.open(history_path, "r", encoding="utf-8") as f:
            content = await f.read()
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            entry = _safe_json_loads(line, source=str(history_path))
            if entry is None:
                continue
            if entry["session_id"] == session_id:
                entry["title"] = title
                updated = True
            lines.append(json.dumps(entry, ensure_ascii=False))
        await self._atomic_write(history_path, "\n".join(lines) + "\n")
        self._invalidate_list_cache()
        if self._redis:
            await self._redis.delete(f"session:{session_id}:meta")  # H-A1: async
        return updated

    async def list_sessions(self) -> list[dict]:
        """列出所有历史会话（带缓存）。"""
        if self._session_list_cache is not None:
            return self._session_list_cache
        if not self._storage_dir:
            return []
        history_path = self._storage_dir / "history.jsonl"
        if not history_path.exists():
            return []
        sessions = []
        async with aiofiles.open(history_path, "r", encoding="utf-8") as f:
            content = await f.read()
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            entry = _safe_json_loads(line, source=str(history_path))
            if entry is None:
                continue
            sid = entry.get("session_id", "")
            try:
                self._validate_session_id(sid)  # A2
            except ValueError:
                logger.warning("Skipping history entry with invalid session_id: %r", sid)
                continue
            transcript_path = self._storage_dir / f"{sid}.jsonl"
            if transcript_path.exists():
                sessions.append(entry)
        sessions.reverse()  # 最新的在前
        self._session_list_cache = sessions
        return sessions

    def _invalidate_list_cache(self) -> None:
        """使 session 列表缓存失效。"""
        self._session_list_cache = None

    async def _redis_set_messages(self, session_id: str, messages: list[dict]) -> None:
        """将消息列表写入 Redis Sorted Set。"""
        if not self._redis:
            return
        key = f"session:{session_id}:messages"
        pipe = self._redis.pipeline()
        pipe.delete(key)
        for msg in messages:
            score = msg.get("timestamp", 0)
            pipe.zadd(key, {json.dumps(msg, ensure_ascii=False): score})
        pipe.expire(key, 86400)  # 24h TTL
        await pipe.execute()  # H-A1: async redis

    async def _redis_get_messages(self, session_id: str) -> list[dict] | None:
        """从 Redis Sorted Set 读取消息。"""
        if not self._redis:
            return None
        key = f"session:{session_id}:messages"
        if not await self._redis.exists(key):  # H-A1: async redis
            return None
        raw = await self._redis.zrange(key, 0, -1)  # H-A1
        if not raw:
            return None
        return [json.loads(item) for item in raw]

    async def persist_messages(self, session_id: str, messages: list[dict]) -> None:
        """Public method: persist messages to Redis cache."""
        await self._redis_set_messages(session_id, messages)  # H-A1: async

    async def restore_messages(self, session_id: str) -> list[dict] | None:
        """Public method: restore messages from cache/storage."""
        return await self._get_all_messages(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """删除会话及其 transcript。"""
        self._validate_session_id(session_id)  # A2
        self._invalidate_list_cache()
        if self._redis:
            await self._redis.delete(f"session:{session_id}:messages", f"session:{session_id}:meta")  # H-A1: async
        self.remove(session_id)
        if not self._storage_dir:
            return False
        # 删除 transcript 文件
        transcript_path = self._storage_dir / f"{session_id}.jsonl"
        deleted = False
        if transcript_path.exists():
            transcript_path.unlink()
            deleted = True
        # 从 history.jsonl 移除（原子写入）
        history_path = self._storage_dir / "history.jsonl"
        if history_path.exists():
            async with aiofiles.open(history_path, "r", encoding="utf-8") as f:
                content = await f.read()
            lines = []
            for line in content.strip().split("\n"):
                if not line.strip():
                    continue
                entry = _safe_json_loads(line, source=str(history_path))
                if entry is None:
                    continue
                if entry["session_id"] != session_id:
                    lines.append(json.dumps(entry, ensure_ascii=False))
            output = "\n".join(lines)
            if lines:
                output += "\n"
            await self._atomic_write(history_path, output)
        return deleted

    async def get_or_restore(self, session_id: str, agent_loop: AgentLoop | None = None) -> ChatSession | None:
        """获取 session，如果不在内存中则从 transcript 恢复。"""
        self._validate_session_id(session_id)  # A2
        session = self.get(session_id)
        if session is not None:
            return session
        # 尝试从 transcript 恢复
        if not self._storage_dir or agent_loop is None:
            return None
        transcript_path = self._storage_dir / f"{session_id}.jsonl"
        if not transcript_path.exists():
            return None
        from agent_framework.transcript import TranscriptReader
        reader = TranscriptReader(transcript_path)
        messages = reader.to_messages()
        agent_loop.load_messages(messages)
        # 创建新的 writer（追加模式）
        writer = TranscriptWriter(transcript_path)
        session = ChatSession(
            session_id=session_id,
            agent_loop=agent_loop,
            transcript_writer=writer,
        )
        self._sessions[session_id] = session
        return session

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
            if now - s.last_accessed > self._ttl  # H-A2: 用 last_accessed 判定空闲
            and (s.task is None or s.task.done())
        ]
        for sid in expired:
            self.remove(sid)
            logger.info("Evicted expired session %s", sid)
