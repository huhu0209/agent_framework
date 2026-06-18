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


async def test_recorder_read_snapshot_returns_last_config_and_prompt(tmp_path: Path) -> None:
    """read_snapshot 从落盘文件读最后 config/system_prompt（session 不在内存兜底）。"""
    bus = EventBus()
    rec = RecordingSubscriber(bus, tmp_path)
    await rec.start()
    await bus.publish({"type": "config", "session_id": "s1", "payload": {"model": "old"}, "timestamp": 1.0})
    await bus.publish({"type": "system_prompt", "session_id": "s1", "payload": {"text": "old"}, "timestamp": 1.0})
    await bus.publish({"type": "config", "session_id": "s1", "payload": {"model": "new"}, "timestamp": 2.0})
    await bus.publish({"type": "system_prompt", "session_id": "s1", "payload": {"text": "new"}, "timestamp": 2.0})
    await asyncio.sleep(0.1)
    await rec.stop()

    snapshot = rec.read_snapshot("s1")
    assert snapshot is not None
    assert [e["type"] for e in snapshot] == ["config", "system_prompt"]
    assert snapshot[0]["payload"]["model"] == "new"  # 最后一次的
    assert snapshot[1]["payload"]["text"] == "new"


def test_recorder_read_snapshot_returns_none_for_unknown(tmp_path: Path) -> None:
    rec = RecordingSubscriber(EventBus(), tmp_path)
    assert rec.read_snapshot("nonexistent") is None


async def test_read_replay_returns_all_events_in_order(tmp_path: Path) -> None:
    """read_replay 返回全量事件（含工具链），按落盘顺序。"""
    bus = EventBus()
    rec = RecordingSubscriber(bus, tmp_path)
    await rec.start()
    await bus.publish({"type": "config", "session_id": "abc", "payload": {"model": "m"}, "timestamp": 1.0})
    await bus.publish({"type": "tool_call", "session_id": "abc", "payload": {"tool_call_id": "tc1"}, "timestamp": 2.0})
    await bus.publish({"type": "tool_result", "session_id": "abc", "payload": {"tool_call_id": "tc1"}, "timestamp": 3.0})
    await asyncio.sleep(0.1)
    await rec.stop()

    events = rec.read_replay("abc")
    assert events is not None
    assert [e["type"] for e in events] == ["config", "tool_call", "tool_result"]


def test_read_replay_returns_none_when_file_missing(tmp_path: Path) -> None:
    rec = RecordingSubscriber(EventBus(), tmp_path)
    assert rec.read_replay("nonexistent") is None
