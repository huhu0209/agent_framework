"""Teams 类型测试。"""

from agent_framework.teams.types import (
    TeammateConfig,
    TeammateStatus,
    TeamMessage,
    TeamNotification,
)


def test_teammate_status_values():
    assert TeammateStatus.WORKING == "working"
    assert TeammateStatus.IDLE == "idle"
    assert TeammateStatus.SHUTDOWN == "shutdown"


def test_teammate_config_defaults():
    config = TeammateConfig(name="alice", role="researcher", system_prompt="你是一个研究员")
    assert config.allowed_tools is None
    assert config.model is None
    assert config.max_idle_seconds == 60


def test_team_message_creation():
    msg = TeamMessage(type="message", from_="lead", to="alice", content="你好", timestamp=1.0)
    assert msg.from_ == "lead"
    assert msg.to == "alice"


def test_team_notification():
    note = TeamNotification(name="alice", status="shutdown")
    assert note.name == "alice"
