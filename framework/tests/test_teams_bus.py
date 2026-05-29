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
