"""A2/A4: SessionManager 路径遍历与 JSON 容错安全测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.session import SessionManager


# --- A2: session_id 路径遍历防护 ---


async def test_delete_session_rejects_path_traversal(tmp_path: Path) -> None:
    """A2: delete_session 对 ../ 型 session_id 应拒绝，不触发路径逃逸。"""
    sm = SessionManager(storage_dir=tmp_path)
    with pytest.raises(ValueError):
        await sm.delete_session("../../etc/passwd")


async def test_get_messages_rejects_path_traversal(tmp_path: Path) -> None:
    """A2: get_messages 对非法 session_id 应拒绝。"""
    sm = SessionManager(storage_dir=tmp_path)
    with pytest.raises(ValueError):
        await sm.get_messages("../secret")


async def test_get_or_restore_rejects_path_traversal(tmp_path: Path) -> None:
    """A2: get_or_restore 对非法 session_id 应拒绝。"""
    sm = SessionManager(storage_dir=tmp_path)
    with pytest.raises(ValueError):
        await sm.get_or_restore("../../etc/passwd", agent_loop=None)


async def test_valid_hex_session_id_accepted(tmp_path: Path) -> None:
    """A2: 合法 32 位 hex session_id 不应抛 ValueError。"""
    sm = SessionManager(storage_dir=tmp_path)
    result = await sm.delete_session("a" * 32)
    assert result is False


# --- A4: JSON 容错 ---


async def test_list_sessions_skips_malformed_lines(tmp_path: Path, caplog) -> None:
    """A4: history.jsonl 含坏行时 list_sessions 应跳过并告警，不抛 500。"""
    sm = SessionManager(storage_dir=tmp_path)
    history = tmp_path / "history.jsonl"
    valid_line = json.dumps({"session_id": "a" * 32, "title": "ok", "created_at": 1.0})
    history.write_text(valid_line + "\n{this is not valid json\n")

    with caplog.at_level("WARNING"):
        sessions = await sm.list_sessions()  # 不应抛 JSONDecodeError

    assert isinstance(sessions, list)  # 坏行被跳过，未崩溃
    assert any("malformed" in rec.message.lower() or "skipping" in rec.message.lower()
               for rec in caplog.records)


async def test_update_title_skips_malformed_lines(tmp_path: Path) -> None:
    """A4: update_title 遇坏行应跳过，不抛 500。"""
    sm = SessionManager(storage_dir=tmp_path)
    history = tmp_path / "history.jsonl"
    history.write_text("{bad json\n")

    result = await sm.update_title("a" * 32, "new title")
    assert result is False


async def test_delete_session_skips_malformed_lines(tmp_path: Path) -> None:
    """A4: delete_session 遇坏行应跳过，不抛 500。"""
    sm = SessionManager(storage_dir=tmp_path)
    history = tmp_path / "history.jsonl"
    history.write_text("{bad json\n")

    result = await sm.delete_session("a" * 32)
    assert result is False
