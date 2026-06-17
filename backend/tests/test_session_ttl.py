"""H-A2: last_accessed TTL 语义测试。"""

from __future__ import annotations

import time
from pathlib import Path

from app.services.session import ChatSession, SessionManager


def test_active_session_not_evicted(tmp_path: Path):
    """H-A2: 活跃会话（创建久但 last_accessed 最近）不被淘汰。"""
    sm = SessionManager(ttl=100, storage_dir=tmp_path)
    s = ChatSession(session_id="a" * 32)
    sm._sessions["a" * 32] = s
    s.created_at = time.time() - 200  # 创建 200s 前（> ttl）
    s.last_accessed = time.time() - 10  # 但 10s 前访问（< ttl）
    sm._evict_expired()
    assert "a" * 32 in sm._sessions  # 活跃保留


def test_idle_session_evicted(tmp_path: Path):
    """H-A2: 空闲会话（创建近但 last_accessed 久）被淘汰。"""
    sm = SessionManager(ttl=100, storage_dir=tmp_path)
    s = ChatSession(session_id="b" * 32)
    sm._sessions["b" * 32] = s
    s.created_at = time.time() - 50  # 创建 50s 前（< ttl）
    s.last_accessed = time.time() - 200  # 但 200s 未访问（> ttl）
    sm._evict_expired()
    assert "b" * 32 not in sm._sessions  # 空闲淘汰


def test_get_updates_last_accessed_not_created(tmp_path: Path):
    """H-A2: get() 更新 last_accessed，不刷新 created_at。"""
    sm = SessionManager(storage_dir=tmp_path)
    s = ChatSession(session_id="c" * 32)
    original_created = 1000.0
    s.created_at = original_created
    sm._sessions["c" * 32] = s
    sm.get("c" * 32)
    assert s.created_at == original_created  # created_at 不变
    assert s.last_accessed > original_created  # last_accessed 更新
