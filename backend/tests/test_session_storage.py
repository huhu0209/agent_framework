"""Task 3: SessionManager 分桶存储测试。"""

from __future__ import annotations

from pathlib import Path

from app.services.session import ChatSession, DEFAULT_BUCKET, SessionManager


class _StubLoop:
    system_prompt_text = ""

    async def run(self, msg, *, resume=False):
        if False:
            yield  # async gen

    def load_messages(self, m):
        pass


async def _mk(sm, **kw):
    return await sm.create(_StubLoop(), **kw)


def test_create_writes_into_bucket_dir(tmp_path: Path):
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    s = asyncio.run(_mk(sm, bucket="myapp_abcd1234", project_path="/tmp/myapp"))
    assert s.bucket == "myapp_abcd1234"
    assert (tmp_path / "myapp_abcd1234" / f"{s.session_id}.jsonl").exists()
    assert (tmp_path / "myapp_abcd1234" / "history.jsonl").exists()


def test_create_default_bucket_writes_default_dir(tmp_path: Path):
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    s = asyncio.run(_mk(sm))
    assert s.bucket == DEFAULT_BUCKET
    assert (tmp_path / DEFAULT_BUCKET / f"{s.session_id}.jsonl").exists()


def test_list_sessions_scoped_to_bucket(tmp_path: Path):
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    a = asyncio.run(_mk(sm, bucket="projA_aaaaaaaa", title="A"))
    b = asyncio.run(_mk(sm, bucket="projB_bbbbbbbb", title="B"))
    lista = asyncio.run(sm.list_sessions(bucket="projA_aaaaaaaa"))
    listb = asyncio.run(sm.list_sessions(bucket="projB_bbbbbbbb"))
    assert [x["session_id"] for x in lista] == [a.session_id]
    assert [x["session_id"] for x in listb] == [b.session_id]


def test_delete_session_removes_only_in_bucket(tmp_path: Path):
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    a = asyncio.run(_mk(sm, bucket="projA_aaaaaaaa"))
    # M3: 兄弟桶会话 — 删除 a 后其文件应仍然存在，证明 delete 只作用于目标桶
    b = asyncio.run(_mk(sm, bucket="projB_bbbbbbbb"))
    assert (tmp_path / "projB_bbbbbbbb" / f"{b.session_id}.jsonl").exists()
    assert asyncio.run(sm.delete_session(a.session_id, bucket="projA_aaaaaaaa"))
    assert not (tmp_path / "projA_aaaaaaaa" / f"{a.session_id}.jsonl").exists()
    assert (tmp_path / "projB_bbbbbbbb" / f"{b.session_id}.jsonl").exists()


def test_get_messages_reads_from_bucket(tmp_path: Path):
    import asyncio

    from agent_framework.transcript import (
        TranscriptEvent,
        TranscriptEventType,
        TranscriptWriter,
    )

    sm = SessionManager(storage_dir=tmp_path)
    a = asyncio.run(_mk(sm, bucket="projA_aaaaaaaa"))
    # 模拟真实写入路径:TranscriptWriter 写一条 user 事件到桶内
    bucket_dir = tmp_path / "projA_aaaaaaaa"
    writer = TranscriptWriter(bucket_dir / f"{a.session_id}.jsonl")
    writer.write(
        TranscriptEvent(
            type=TranscriptEventType.USER,
            timestamp=1.0,
            content="hi",
        )
    )
    writer.close()
    sm.remove(a.session_id)  # 清内存,走冷读
    msgs = asyncio.run(sm.get_messages(a.session_id, bucket="projA_aaaaaaaa"))
    assert msgs is not None
    assert msgs[0][0]["content"] == "hi"
