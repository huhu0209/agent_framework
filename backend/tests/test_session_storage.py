"""Task 3: SessionManager 分桶存储测试。"""

from __future__ import annotations

import json
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


def test_create_persists_agent_name_to_history(tmp_path: Path):
    """M1: create 时 agent_name 持久化到 history.jsonl,供冷恢复读取。"""
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    s = asyncio.run(_mk(sm, agent_name="reviewer"))
    history = (tmp_path / DEFAULT_BUCKET / "history.jsonl").read_text(encoding="utf-8")
    entry = json.loads(history.strip().split("\n")[-1])
    assert entry["agent_name"] == "reviewer"
    assert entry["session_id"] == s.session_id


def test_get_or_restore_reads_agent_name_from_disk(tmp_path: Path):
    """M1: 冷恢复(内存淘汰)后,get_or_restore 从 history.jsonl 回填 agent_name,而非静默回退 default。"""
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    s = asyncio.run(_mk(sm, agent_name="reviewer"))
    sid = s.session_id
    sm.remove(sid)  # 模拟重启/TTL 淘汰:清内存,磁盘保留
    assert sid not in sm._sessions

    restored = asyncio.run(sm.get_or_restore(sid, _StubLoop(), bucket=DEFAULT_BUCKET))
    assert restored is not None
    assert restored.agent_name == "reviewer"


def test_get_session_agent_name_falls_back_to_disk(tmp_path: Path):
    """M1: get_session_agent_name 内存命中直接返回,内存未命中回退磁盘 history。"""
    import asyncio

    sm = SessionManager(storage_dir=tmp_path)
    s = asyncio.run(_mk(sm, agent_name="reviewer"))
    sid = s.session_id
    # 内存命中
    assert asyncio.run(sm.get_session_agent_name(sid, bucket=DEFAULT_BUCKET)) == "reviewer"
    sm.remove(sid)
    # 内存未命中 → 磁盘 history
    assert asyncio.run(sm.get_session_agent_name(sid, bucket=DEFAULT_BUCKET)) == "reviewer"


def test_get_session_agent_name_legacy_entry_returns_none(tmp_path: Path):
    """M1 向后兼容:旧 history entry 无 agent_name 字段 → 返回 None(=default)。"""
    import asyncio

    bucket_dir = tmp_path / DEFAULT_BUCKET
    bucket_dir.mkdir(parents=True)
    legacy_sid = "a" * 32
    (bucket_dir / "history.jsonl").write_text(
        json.dumps({"session_id": legacy_sid, "bucket": DEFAULT_BUCKET, "title": "old"}) + "\n",
        encoding="utf-8",
    )
    sm = SessionManager(storage_dir=tmp_path)
    name = asyncio.run(sm.get_session_agent_name(legacy_sid, bucket=DEFAULT_BUCKET))
    assert name is None
