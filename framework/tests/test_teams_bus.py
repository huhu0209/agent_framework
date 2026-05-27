"""MessageBus 测试 — JSONL 文件收件箱。"""

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
