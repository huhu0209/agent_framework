"""H-A6: history.jsonl 并发写测试。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.services.session import SessionManager


async def test_session_manager_has_history_lock() -> None:
    """H-A6: SessionManager 有 _history_lock 保护并发 append。"""
    sm = SessionManager()
    assert hasattr(sm, "_history_lock")
    assert isinstance(sm._history_lock, asyncio.Lock)


async def test_append_history_concurrent_produces_complete_lines(tmp_path: Path) -> None:
    """H-A6: 并发 _append_history 每行完整 JSON（锁保护，不交错）。"""
    sm = SessionManager(storage_dir=tmp_path)
    await asyncio.gather(*[
        sm._append_history(f"{i:032x}", f"title {i}") for i in range(20)
    ])

    history = (tmp_path / "history.jsonl").read_text()
    lines = [l for l in history.strip().split("\n") if l.strip()]
    assert len(lines) == 20  # 20 行
    for line in lines:
        entry = json.loads(line)  # 每行完整 JSON，不抛
        assert "session_id" in entry
