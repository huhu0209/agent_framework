"""Redis 缓存层测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.session import SessionManager

# 检查 Redis 是否可用
redis_available = False
try:
    import redis as redis_lib
    _r = redis_lib.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    _r.ping()
    _r.close()
    redis_available = True
except Exception:
    pass

pytestmark = pytest.mark.skipif(not redis_available, reason="Redis not available")


@pytest.fixture
def rdb():
    import redis as redis_lib
    r = redis_lib.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    r.flushdb()
    yield r
    r.flushdb()
    r.close()


@pytest.fixture
def sm_with_redis(tmp_path: Path, rdb) -> SessionManager:
    storage_dir = tmp_path / "sessions"
    return SessionManager(storage_dir=storage_dir, redis_client=rdb)


def test_get_messages_caches_to_redis_after_cold_read(sm_with_redis: SessionManager, rdb) -> None:
    """冷读后应将消息回填到 Redis。"""
    sm = sm_with_redis
    sid = _create_session_with_message(sm)

    # 从内存移除，模拟 TTL 过期
    sm.remove(sid)
    assert sm.get(sid) is None

    # 冷读 — 应从 JSONL 读取并回填 Redis
    messages = sm.get_messages(sid)
    assert messages is not None
    assert any(m["role"] == "user" for m in messages)

    # 验证 Redis 已缓存
    cached = rdb.zrange(f"session:{sid}:messages", 0, -1)
    assert len(cached) > 0


def test_get_messages_hits_redis_cache(sm_with_redis: SessionManager, rdb) -> None:
    """Redis 命中时应直接返回，不读 JSONL。"""
    sm = sm_with_redis
    sid = _create_session_with_message(sm)

    sm.remove(sid)

    # 第一次冷读（回填 Redis）
    sm.get_messages(sid)

    # 删除 JSONL 文件 — 如果 Redis 不起作用就会失败
    jsonl_path = sm._storage_dir / f"{sid}.jsonl"
    jsonl_path.unlink()

    # 第二次应从 Redis 命中
    messages = sm.get_messages(sid)
    assert messages is not None
    assert any(m["role"] == "user" for m in messages)


def test_delete_session_clears_redis(sm_with_redis: SessionManager, rdb) -> None:
    """删除 session 应同时清理 Redis 缓存。"""
    sm = sm_with_redis
    sid = _create_session_with_message(sm)

    # 触发缓存
    sm.get_messages(sid)

    # 删除
    sm.delete_session(sid)

    # Redis 应已清理
    assert rdb.exists(f"session:{sid}:messages") == 0


def _create_session_with_message(sm: SessionManager) -> str:
    """辅助：创建 session 并写入一条消息到 transcript 和内存。"""
    from unittest.mock import MagicMock

    loop = MagicMock()
    session = sm.create(loop, title="test")

    # 写入内存
    session.messages.append({"role": "user", "content": "hello", "timestamp": 1000.0})
    session.messages.append({"role": "agent", "blocks": [{"type": "text", "text": "hi"}], "timestamp": 1001.0})

    # 直接写入 JSONL（模拟 TranscriptWriter 的输出）
    jsonl_path = sm._storage_dir / f"{session.session_id}.jsonl"
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "content": "hello", "timestamp": 1000.0}, ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "assistant", "content": [{"type": "text", "text": "hi"}], "timestamp": 1001.0}, ensure_ascii=False) + "\n")

    return session.session_id
