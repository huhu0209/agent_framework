"""TranscriptWriter 测试。"""

import json
from pathlib import Path

from agent_framework.transcript.types import TranscriptEvent, TranscriptEventType
from agent_framework.transcript.writer import TranscriptWriter


def test_write_single_event(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)

    ev = TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hello")
    writer.write(ev)
    writer.close()

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["type"] == "user"
    assert data["content"] == "hello"
    assert data["timestamp"] == 1.0


def test_write_multiple_events(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)

    writer.write(TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hi"))
    writer.write(TranscriptEvent(type=TranscriptEventType.ASSISTANT, timestamp=2.0, content=[{"type": "text", "text": "hello"}]))
    writer.close()

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["type"] == "user"
    assert json.loads(lines[1])["type"] == "assistant"


def test_flushes_to_disk_after_each_write(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)

    writer.write(TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="hi"))
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1
    writer.close()


def test_append_to_existing_file(tmp_path: Path):
    path = tmp_path / "test.jsonl"
    writer = TranscriptWriter(path)
    writer.write(TranscriptEvent(type=TranscriptEventType.USER, timestamp=1.0, content="first"))
    writer.close()

    writer = TranscriptWriter(path)
    writer.write(TranscriptEvent(type=TranscriptEventType.USER, timestamp=2.0, content="second"))
    writer.close()

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2


def test_creates_parent_directory(tmp_path: Path):
    path = tmp_path / "subdir" / "deep" / "test.jsonl"
    writer = TranscriptWriter(path)
    writer.write(TranscriptEvent(type=TranscriptEventType.SYSTEM, timestamp=0.0, content="sys"))
    writer.close()
    assert path.exists()
