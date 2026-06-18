"""MessageBus 测试 — JSONL 文件收件箱。"""

import os
from unittest.mock import patch

from agent_framework.teams.bus import MessageBus


def test_send_and_read(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "你好")

    inbox = bus.read_inbox("alice")
    assert len(inbox) == 1
    assert inbox[0].content == "你好"
    assert inbox[0].from_ == "lead"


def test_read_clears_inbox(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "消息1")
    bus.read_inbox("alice")

    inbox = bus.read_inbox("alice")
    assert inbox == []


def test_read_empty_inbox(tmp_path):
    bus = MessageBus(tmp_path)
    inbox = bus.read_inbox("alice")
    assert inbox == []


def test_broadcast_skips_sender(tmp_path):
    bus = MessageBus(tmp_path)
    bus.broadcast("alice", ["alice", "bob", "carol"], "同步消息")

    assert bus.read_inbox("alice") == []
    assert len(bus.read_inbox("bob")) == 1
    assert len(bus.read_inbox("carol")) == 1


def test_send_with_type(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "请关闭", msg_type="shutdown_request")

    inbox = bus.read_inbox("alice")
    assert inbox[0].type == "shutdown_request"


# --- 原子清零测试 ---


def test_read_inbox_atomic_swap(tmp_path):
    """read_inbox 原子清零：返回消息后文件内容为空。"""
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "消息1")
    bus.send("lead", "alice", "消息2")

    inbox = bus.read_inbox("alice")
    assert len(inbox) == 2
    assert inbox[0].content == "消息1"
    assert inbox[1].content == "消息2"

    # 验证文件已清空
    path = tmp_path / "inbox" / "alice.jsonl"
    assert path.read_text() == ""


def test_read_inbox_atomic_no_message_loss_on_failure(tmp_path):
    """os.replace 失败时消息不丢失：read_inbox 仍返回消息，下次可重复读取。"""
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "关键消息")

    with patch("agent_framework.teams.bus.os.replace", side_effect=OSError("模拟崩溃")):
        inbox = bus.read_inbox("alice")

    # 即使清零失败，消息仍被返回
    assert len(inbox) == 1
    assert inbox[0].content == "关键消息"

    # 消息仍在文件中，可重复读取
    inbox2 = bus.read_inbox("alice")
    assert len(inbox2) == 1
    assert inbox2[0].content == "关键消息"


def test_read_inbox_atomic_cleanup_tempfile(tmp_path):
    """os.replace 失败时临时文件被清理。"""
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "测试清理")

    with patch("agent_framework.teams.bus.os.replace", side_effect=OSError("模拟崩溃")) as mock_replace, \
         patch("agent_framework.teams.bus.os.unlink") as mock_unlink:
        bus.read_inbox("alice")

    # 验证 os.unlink 被调用以清理临时文件
    assert mock_unlink.called


# --- H-G4: 精确清零 ---


def test_read_inbox_preserves_unparseable_lines(tmp_path):
    """H-G4: 精确清零——不可解析的非消息行不被清零（只删本次读到的消息行）。"""
    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "valid")
    path = tmp_path / "inbox" / "alice.jsonl"
    # 追加一行不可解析内容（模拟外部写入/损坏行）
    with open(path, "a", encoding="utf-8") as f:
        f.write("NOT-JSON-LINE\n")

    inbox = bus.read_inbox("alice")
    assert len(inbox) == 1  # 只解析出 valid

    final = path.read_text()
    assert "NOT-JSON-LINE" in final  # 精确清零保留非消息行
    assert "valid" not in final


def test_read_inbox_keeps_message_appended_between_reads(tmp_path, monkeypatch):
    """H-G4 补充：read 窗口期间追加的有效消息行被保留（精确清零的并发追加分支）。"""
    import json as _json
    from pathlib import Path

    bus = MessageBus(tmp_path)
    bus.send("lead", "alice", "first")
    path = tmp_path / "inbox" / "alice.jsonl"

    original_read_text = Path.read_text
    calls = {"n": 0}

    def spy_read_text(self, *args, **kwargs):
        result = original_read_text(self, *args, **kwargs)
        if self == path:
            calls["n"] += 1
            if calls["n"] == 2:  # read_inbox 内的重读（精确清零特有）
                with open(path, "a", encoding="utf-8") as f:
                    f.write(_json.dumps({
                        "type": "message", "from_": "bob", "to": "alice",
                        "content": "concurrent", "timestamp": 999.0,
                    }) + "\n")
                return original_read_text(self, *args, **kwargs)  # 追加后重读
        return result

    monkeypatch.setattr(Path, "read_text", spy_read_text)
    inbox = bus.read_inbox("alice")
    assert len(inbox) == 1 and inbox[0].content == "first"  # 只返回第一次读的批次
    final = original_read_text(path)
    assert "concurrent" in final  # read 窗口期间追加的消息保留
