"""Redis 运行时失败降级测试。

main.py 把 Redis 定位为「可选缓存层，失败时降级」。启动容错之外，
运行时 Redis 抖动 / 断连同样必须降级（读返回 None 走 JSONL，写静默），
绝不能让可选缓存把核心读 / 写路径拖垮成 500。
这些测试锁定该契约——不依赖真实 Redis，用 mock 注入异常。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import redis.exceptions

from app.services.session import SessionManager


def _raising_redis(method: str) -> MagicMock:
    """构造 mock redis，指定方法抛 TimeoutError（模拟运行时连接超时）。"""
    fake = MagicMock()
    setattr(fake, method, AsyncMock(side_effect=redis.exceptions.TimeoutError("boom")))
    return fake


class TestRedisRuntimeFallback:
    async def test_get_messages_swallows_redis_timeout(self) -> None:
        """读路径：redis.exists 超时 → 返回 None（降级走 JSONL），不抛。"""
        sm = SessionManager(redis_client=_raising_redis("exists"))
        assert await sm._redis_get_messages("a" * 32) is None

    async def test_get_messages_swallows_redis_timeout_on_zrange(self) -> None:
        """读路径：exists 通过但 zrange 超时 → 仍返回 None，不抛。"""
        fake = MagicMock()
        fake.exists = AsyncMock(return_value=True)
        fake.zrange = AsyncMock(side_effect=redis.exceptions.TimeoutError("boom"))
        sm = SessionManager(redis_client=fake)
        assert await sm._redis_get_messages("a" * 32) is None

    async def test_set_messages_swallows_redis_timeout(self) -> None:
        """写路径：pipeline 超时 → 静默，不抛（消息已落 JSONL，缓存失败无所谓）。"""
        fake = MagicMock()
        pipe = MagicMock()
        pipe.execute = AsyncMock(side_effect=redis.exceptions.TimeoutError("boom"))
        fake.pipeline.return_value = pipe
        sm = SessionManager(redis_client=fake)
        await sm._redis_set_messages("a" * 32, [{"timestamp": 1, "content": "x"}])  # 不抛即通过

    async def test_delete_session_swallows_redis_timeout(self, tmp_path: Path) -> None:
        """删会话：redis.delete 超时 → 静默，transcript 文件照常删除。"""
        from app.services.session import DEFAULT_BUCKET

        storage_dir = tmp_path / "sessions"
        bucket_dir = storage_dir / DEFAULT_BUCKET
        bucket_dir.mkdir(parents=True)
        sid = "a" * 32
        (bucket_dir / f"{sid}.jsonl").write_text(
            '{"role":"user","content":"hi","timestamp":1}\n'
        )
        sm = SessionManager(storage_dir=storage_dir, redis_client=_raising_redis("delete"))
        await sm.delete_session(sid)  # 不抛即通过
        assert not (bucket_dir / f"{sid}.jsonl").exists()

    async def test_update_title_swallows_redis_timeout(self, tmp_path: Path) -> None:
        """重命名：redis.delete(meta) 超时 → 静默，history.jsonl 标题照常更新。"""
        from app.services.session import DEFAULT_BUCKET

        storage_dir = tmp_path / "sessions"
        bucket_dir = storage_dir / DEFAULT_BUCKET
        bucket_dir.mkdir(parents=True)
        sid = "a" * 32
        (bucket_dir / "history.jsonl").write_text(
            json.dumps({"session_id": sid, "title": "old", "created_at": 1}) + "\n"
        )
        sm = SessionManager(storage_dir=storage_dir, redis_client=_raising_redis("delete"))
        await sm.update_title(sid, "new")  # 不抛即通过
        saved = (bucket_dir / "history.jsonl").read_text()
        assert "new" in saved and "old" not in saved
