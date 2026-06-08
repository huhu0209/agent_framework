"""Session 管理 — 内存存储，含 TTL 淘汰，可选持久化。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.transcript import TranscriptWriter

logger = logging.getLogger(__name__)

SESSION_TTL = 3600  # 1 hour


@dataclass
class ChatSession:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    agent_loop: AgentLoop | None = None
    task: asyncio.Task | None = None  # type: ignore[type-arg]
    created_at: float = field(default_factory=time.time)
    transcript_writer: TranscriptWriter | None = None


class SessionManager:
    """管理活跃 session 的生命周期，含 TTL 自动淘汰。"""

    def __init__(self, ttl: float = SESSION_TTL, storage_dir: Path | None = None) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._ttl = ttl
        self._storage_dir = storage_dir
        self._cleanup_task: asyncio.Task | None = None  # type: ignore[type-arg]

    def start_cleanup(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

    def create(self, agent_loop: AgentLoop, *, title: str = "") -> ChatSession:
        sid = uuid.uuid4().hex
        writer = None
        if self._storage_dir:
            transcript_path = self._storage_dir / f"{sid}.jsonl"
            writer = TranscriptWriter(transcript_path)
            self._append_history(sid, title or "新会话")
        session = ChatSession(session_id=sid, agent_loop=agent_loop, transcript_writer=writer)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> ChatSession | None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.created_at = time.time()
        return session

    def get_messages(self, session_id: str) -> list[dict] | None:
        """获取 session 的消息列表，支持从 transcript 恢复。"""
        session = self._sessions.get(session_id)
        if session is not None:
            return session.messages
        if not self._storage_dir:
            return None
        transcript_path = self._storage_dir / f"{session_id}.jsonl"
        if not transcript_path.exists():
            return None
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

    def _append_history(self, session_id: str, title: str) -> None:
        if not self._storage_dir:
            return
        history_path = self._storage_dir / "history.jsonl"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        entry = json.dumps({
            "session_id": session_id,
            "title": title,
            "created_at": time.time(),
        }, ensure_ascii=False)
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def update_title(self, session_id: str, title: str) -> bool:
        """更新 history.jsonl 中的标题，返回是否实际更新。"""
        if not self._storage_dir:
            return False
        history_path = self._storage_dir / "history.jsonl"
        if not history_path.exists():
            return False
        lines = []
        updated = False
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry["session_id"] == session_id:
                    entry["title"] = title
                    updated = True
                lines.append(json.dumps(entry, ensure_ascii=False))
        with open(history_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return updated

    def list_sessions(self) -> list[dict]:
        """列出所有历史会话。"""
        if not self._storage_dir:
            return []
        history_path = self._storage_dir / "history.jsonl"
        if not history_path.exists():
            return []
        sessions = []
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                transcript_path = self._storage_dir / f"{entry['session_id']}.jsonl"
                if transcript_path.exists():
                    sessions.append(entry)
        sessions.reverse()  # 最新的在前
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除会话及其 transcript。"""
        self.remove(session_id)
        if not self._storage_dir:
            return False
        # 删除 transcript 文件
        transcript_path = self._storage_dir / f"{session_id}.jsonl"
        deleted = False
        if transcript_path.exists():
            transcript_path.unlink()
            deleted = True
        # 从 history.jsonl 移除
        history_path = self._storage_dir / "history.jsonl"
        if history_path.exists():
            lines = []
            with open(history_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry["session_id"] != session_id:
                        lines.append(json.dumps(entry, ensure_ascii=False))
            with open(history_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                if lines:
                    f.write("\n")
        return deleted

    def get_or_restore(self, session_id: str, agent_loop: AgentLoop | None = None) -> ChatSession | None:
        """获取 session，如果不在内存中则从 transcript 恢复。"""
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
            if now - s.created_at > self._ttl
        ]
        for sid in expired:
            self.remove(sid)
            logger.info("Evicted expired session %s", sid)
