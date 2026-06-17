"""H-A1: redis 调用 async 测试（不依赖真实 redis，用 mock）。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


class TestRedisAsync:
    """H-A1: redis 调用必须 async（不阻塞事件循环）。用 mock，不依赖真实 redis。"""

    async def test_redis_set_messages_awaits_pipeline_execute(self):
        from app.services.session import SessionManager
        fake_redis = MagicMock()
        fake_pipe = MagicMock()
        fake_pipe.execute = AsyncMock()
        fake_redis.pipeline.return_value = fake_pipe

        sm = SessionManager(redis_client=fake_redis)
        await sm._redis_set_messages("a" * 32, [{"timestamp": 1, "content": "x"}])

        fake_pipe.execute.assert_awaited_once()  # H-A1: execute 被 await

    async def test_redis_get_messages_is_async(self):
        from app.services.session import SessionManager
        fake_redis = MagicMock()
        fake_redis.exists = AsyncMock(return_value=False)

        sm = SessionManager(redis_client=fake_redis)
        result = await sm._redis_get_messages("a" * 32)  # H-A1: async, 不抛 TypeError
        assert result is None

    async def test_redis_delete_is_awaited(self):
        """H-A1: update_title/delete_session 的 redis.delete 被 await。"""
        from app.services.session import SessionManager
        fake_redis = MagicMock()
        fake_redis.delete = AsyncMock(return_value=1)

        sm = SessionManager(redis_client=fake_redis)
        # delete_session 调用 await self._redis.delete(...)
        await sm.delete_session("a" * 32)
        fake_redis.delete.assert_awaited()
