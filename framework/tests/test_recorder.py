import asyncio
from pathlib import Path

from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.recorder import RecordingSubscriber


async def test_recorder_writes_events_by_session(tmp_path: Path) -> None:
    bus = EventBus()
    rec = RecordingSubscriber(bus, tmp_path)
    await rec.start()
    await bus.publish({"type": "config", "session_id": "abc123", "payload": {}, "timestamp": 1.0})
    await bus.publish({"type": "tool_call", "session_id": "abc123", "payload": {}, "timestamp": 2.0})
    await asyncio.sleep(0.1)
    await rec.stop()

    lines = (tmp_path / "abc123.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert '"config"' in lines[0]


async def test_recorder_isolates_sessions(tmp_path: Path) -> None:
    bus = EventBus()
    rec = RecordingSubscriber(bus, tmp_path)
    await rec.start()
    await bus.publish({"type": "config", "session_id": "aaa", "payload": {}, "timestamp": 1.0})
    await bus.publish({"type": "config", "session_id": "bbb", "payload": {}, "timestamp": 2.0})
    await asyncio.sleep(0.1)
    await rec.stop()
    assert (tmp_path / "aaa.jsonl").exists()
    assert (tmp_path / "bbb.jsonl").exists()


async def test_recorder_sanitizes_session_id(tmp_path: Path) -> None:
    """路径遍历防护：含 ../ 的 session_id 被清洗。"""
    bus = EventBus()
    rec = RecordingSubscriber(bus, tmp_path)
    await rec.start()
    await bus.publish({"type": "config", "session_id": "../etc/passwd", "payload": {}, "timestamp": 1.0})
    await asyncio.sleep(0.1)
    await rec.stop()
    assert not (tmp_path / ".." / "etc").exists()  # 没越界
    assert any(p.suffix == ".jsonl" for p in tmp_path.iterdir())
