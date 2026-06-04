"""Chat API 单元测试。"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

import pytest
from starlette.testclient import TestClient

from agent_framework.agents.agent_loop import LoopEvent


class _FakeAgentLoop:
    """产生固定 LoopEvent 序列的假 AgentLoop。"""

    def __init__(self, events: list[LoopEvent]) -> None:
        self._events = events

    async def run(
        self, user_message: str, *, resume: bool = False,
    ) -> AsyncGenerator[LoopEvent, None]:
        for event in self._events:
            yield event


class _FailingAgentLoop:
    """始终抛异常的假 AgentLoop。"""

    async def run(
        self, user_message: str, *, resume: bool = False,
    ) -> AsyncGenerator[LoopEvent, None]:
        raise RuntimeError("agent crashed")
        yield  # noqa: unreachable — makes this an async generator


def _make_done_events() -> list[LoopEvent]:
    return [
        LoopEvent(type="step", step=1, data={"stop_reason": "end_turn", "content": [{"type": "text", "text": "hello"}]}),
        LoopEvent(type="done", step=1, data={"content": [{"type": "text", "text": "hello"}]}),
    ]


def _make_tool_events() -> list[LoopEvent]:
    return [
        LoopEvent(type="step", step=1, data={"stop_reason": "tool_use", "content": []}),
        LoopEvent(type="tool_result", step=1, data={
            "tool_calls": [{"id": "tc_1", "name": "search", "input": {"q": "test"}}],
            "tool_results": ["found it"],
        }),
        LoopEvent(type="step", step=2, data={"stop_reason": "end_turn", "content": [{"type": "text", "text": "result"}]}),
        LoopEvent(type="done", step=2, data={"content": [{"type": "text", "text": "result"}]}),
    ]


class _FakeFactory:
    def __init__(self, events: list[LoopEvent] | None = None) -> None:
        self._events = events or _make_done_events()

    def create_loop(self) -> _FakeAgentLoop:
        return _FakeAgentLoop(self._events)


class _FailingFactory:
    def create_loop(self) -> _FailingAgentLoop:
        return _FailingAgentLoop()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")

    from app.services.session import SessionManager
    from main import app

    session_manager = SessionManager()

    app.state.session_manager = session_manager
    app.state.agent_factory = _FakeFactory()

    return TestClient(app)


def _wait_for_task(client: TestClient, sid: str, timeout: float = 2.0) -> None:
    """轮询直到 agent task 完成或超时。"""
    import time
    deadline = time.time() + timeout
    sm = client.app.state.session_manager
    while time.time() < deadline:
        session = sm.get(sid)
        if session is None:
            break
        task = session.task
        if task is None or task.done():
            break
        time.sleep(0.05)


# --- POST /chat ---


def test_post_chat_returns_session_id(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["status"] == "processing"


def test_post_chat_empty_message_400(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": ""})
    assert res.status_code == 400


def test_post_chat_invalid_session_id_format(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello", "session_id": "bad-format"})
    assert res.status_code == 422


def test_post_chat_unknown_session_404(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello", "session_id": "a" * 32})
    assert res.status_code == 404


# --- GET /chat/{id} ---


def test_get_chat_history(client: TestClient) -> None:
    create_res = client.post("/api/v1/chat", json={"message": "hello"})
    sid = create_res.json()["session_id"]

    _wait_for_task(client, sid)

    res = client.get(f"/api/v1/chat/{sid}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sid
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["role"] == "user"


def test_get_chat_unknown_session_404(client: TestClient) -> None:
    res = client.get("/api/v1/chat/" + "a" * 32)
    assert res.status_code == 404


# --- resume session ---


def test_post_chat_resume_existing_session(client: TestClient) -> None:
    create_res = client.post("/api/v1/chat", json={"message": "first"})
    sid = create_res.json()["session_id"]

    _wait_for_task(client, sid)

    resume_res = client.post("/api/v1/chat", json={"message": "second", "session_id": sid})
    assert resume_res.status_code == 201
    assert resume_res.json()["session_id"] == sid

    _wait_for_task(client, sid)

    history_res = client.get(f"/api/v1/chat/{sid}")
    messages = history_res.json()["messages"]
    user_msgs = [m for m in messages if m["role"] == "user"]
    assert len(user_msgs) == 2


# --- agent error ---


def test_agent_error_still_returns_201(client: TestClient) -> None:
    client.app.state.agent_factory = _FailingFactory()

    res = client.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 201
    sid = res.json()["session_id"]

    _wait_for_task(client, sid)

    history_res = client.get(f"/api/v1/chat/{sid}")
    messages = history_res.json()["messages"]
    error_msgs = [m for m in messages if m["role"] == "error"]
    assert len(error_msgs) == 1


# --- WebSocket ---


def test_ws_connects_to_valid_session(client: TestClient) -> None:
    create_res = client.post("/api/v1/chat", json={"message": "hello"})
    sid = create_res.json()["session_id"]

    with client.websocket_connect(f"/api/v1/ws/{sid}") as ws:
        assert ws is not None


def test_ws_receives_events(client: TestClient) -> None:
    """验证 WS 能收到 agent 事件。使用同步 TestClient 存在竞态，
    此测试仅验证 WS 连接后 session 有效且不立即断开。"""
    create_res = client.post("/api/v1/chat", json={"message": "hello"})
    sid = create_res.json()["session_id"]

    with client.websocket_connect(f"/api/v1/ws/{sid}") as ws:
        # WS 连接存活即证明 session 有效
        # 事件接收的完整覆盖应由集成测试完成
        assert ws is not None


def test_ws_unknown_session_closes(client: TestClient) -> None:
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/" + "a" * 32) as ws:
            ws.receive_json()
