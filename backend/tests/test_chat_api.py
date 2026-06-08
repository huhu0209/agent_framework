"""Chat API 单元测试 — SSE 模式。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
from starlette.testclient import TestClient

from agent_framework.agents.agent_loop import LoopEvent


class _FakeAgentLoop:
    """产生固定 LoopEvent 序列的假 AgentLoop。"""

    def __init__(self, events: list[LoopEvent]) -> None:
        self._events = events

    def load_messages(self, messages: list[Any]) -> None:
        """noop — 支持 transcript 恢复路径。"""

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


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """解析 SSE 文本为 (event_type, payload) 列表。"""
    events: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = ""
        data = ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if event_type and data:
            events.append((event_type, json.loads(data)))
    return events


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


# --- POST /chat (SSE) ---


def test_post_chat_returns_sse_stream(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    assert "X-Session-Id" in res.headers

    events = _parse_sse(res.text)
    event_types = [t for t, _ in events]
    assert "done" in event_types
    assert "shutdown" in event_types


def test_post_chat_sse_done_contains_content(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello"})
    events = _parse_sse(res.text)
    done_events = [(t, p) for t, p in events if t == "done"]
    assert len(done_events) >= 1
    first_done_payload = done_events[0][1]
    assert "content" in first_done_payload
    assert first_done_payload["content"][0]["text"] == "hello"


def test_post_chat_empty_message_400(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": ""})
    assert res.status_code == 400


def test_post_chat_invalid_session_id_format(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello", "session_id": "bad-format"})
    assert res.status_code == 422


def test_post_chat_unknown_session_404(client: TestClient) -> None:
    res = client.post("/api/v1/chat", json={"message": "hello", "session_id": "a" * 32})
    assert res.status_code == 404


def test_post_chat_tool_events(client: TestClient) -> None:
    client.app.state.agent_factory = _FakeFactory(_make_tool_events())

    res = client.post("/api/v1/chat", json={"message": "search test"})
    assert res.status_code == 200

    events = _parse_sse(res.text)
    event_types = [t for t, _ in events]
    assert "thinking" in event_types
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "done" in event_types
    assert "shutdown" in event_types


# --- GET /chat/{id} ---


def test_get_chat_history(client: TestClient) -> None:
    create_res = client.post("/api/v1/chat", json={"message": "hello"})
    sid = create_res.headers["X-Session-Id"]

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
    sid = create_res.headers["X-Session-Id"]

    resume_res = client.post("/api/v1/chat", json={"message": "second", "session_id": sid})
    assert resume_res.status_code == 200
    assert resume_res.headers["X-Session-Id"] == sid

    history_res = client.get(f"/api/v1/chat/{sid}")
    messages = history_res.json()["messages"]
    user_msgs = [m for m in messages if m["role"] == "user"]
    assert len(user_msgs) == 2


# --- agent error ---


def test_agent_error_sends_error_event(client: TestClient) -> None:
    client.app.state.agent_factory = _FailingFactory()

    res = client.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 200

    events = _parse_sse(res.text)
    event_types = [t for t, _ in events]
    assert "error" in event_types
    assert "shutdown" in event_types

    # 错误也保存到历史
    sid = res.headers["X-Session-Id"]
    history_res = client.get(f"/api/v1/chat/{sid}")
    messages = history_res.json()["messages"]
    error_msgs = [m for m in messages if m["role"] == "error"]
    assert len(error_msgs) == 1


# --- Transcript 持久化 ---


@pytest.fixture
def client_with_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """带持久化存储的测试客户端。"""
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")

    from app.services.session import SessionManager
    from main import app

    storage_dir = tmp_path / "sessions"
    session_manager = SessionManager(storage_dir=storage_dir)

    app.state.session_manager = session_manager
    app.state.agent_factory = _FakeFactory()

    return TestClient(app)


def test_transcript_file_created_after_chat(client_with_storage: TestClient, tmp_path: Path) -> None:
    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 200
    sid = res.headers["X-Session-Id"]

    transcript_path = tmp_path / "sessions" / f"{sid}.jsonl"
    assert transcript_path.exists()
    content = transcript_path.read_text()
    assert len(content) > 0
    first_line = content.strip().split("\n")[0]
    data = json.loads(first_line)
    assert data["type"] in ("system", "user")


def test_list_sessions_returns_created_session(client_with_storage: TestClient) -> None:
    client_with_storage.post("/api/v1/chat", json={"message": "hello world"})

    res = client_with_storage.get("/api/v1/sessions")
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) >= 1
    assert "session_id" in sessions[0]
    assert "title" in sessions[0]


def test_delete_session_removes_transcript(client_with_storage: TestClient, tmp_path: Path) -> None:
    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    transcript_path = tmp_path / "sessions" / f"{sid}.jsonl"
    assert transcript_path.exists()

    del_res = client_with_storage.delete(f"/api/v1/sessions/{sid}")
    assert del_res.status_code == 200
    assert not transcript_path.exists()


def test_session_restored_from_transcript(client_with_storage: TestClient, tmp_path: Path) -> None:
    # 创建会话并聊天
    res = client_with_storage.post("/api/v1/chat", json={"message": "first message"})
    sid = res.headers["X-Session-Id"]

    # 从内存中移除 session（模拟 TTL 过期）
    sm = client_with_storage.app.state.session_manager
    sm.remove(sid)
    assert sm.get(sid) is None

    # 用同一个 session_id 发消息 — 应该从 transcript 恢复
    resume_res = client_with_storage.post(
        "/api/v1/chat", json={"message": "second message", "session_id": sid}
    )
    assert resume_res.status_code == 200


def test_session_title_updated_on_first_message(client_with_storage: TestClient) -> None:
    res = client_with_storage.post(
        "/api/v1/chat", json={"message": "hello this is a long message that should be truncated"}
    )
    sid = res.headers["X-Session-Id"]

    list_res = client_with_storage.get("/api/v1/sessions")
    sessions = list_res.json()
    matching = [s for s in sessions if s["session_id"] == sid]
    assert len(matching) == 1
    assert matching[0]["title"] == "hello this is a long message that should be trunca"


def test_rename_session(client_with_storage: TestClient) -> None:
    # 先创建一个会话
    resp = client_with_storage.post("/api/v1/chat", json={"message": "hello world"})
    session_id = resp.headers["X-Session-Id"]

    # 重命名
    resp = client_with_storage.patch(f"/api/v1/sessions/{session_id}", json={"title": "My Chat"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # 验证标题已更新
    resp = client_with_storage.get("/api/v1/sessions")
    sessions = resp.json()
    target = next(s for s in sessions if s["session_id"] == session_id)
    assert target["title"] == "My Chat"


def test_rename_session_empty_title_422(client_with_storage: TestClient) -> None:
    resp = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = resp.headers["X-Session-Id"]
    resp = client_with_storage.patch(f"/api/v1/sessions/{sid}", json={"title": "   "})
    assert resp.status_code == 422


def test_rename_session_title_too_long_422(client_with_storage: TestClient) -> None:
    resp = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = resp.headers["X-Session-Id"]
    resp = client_with_storage.patch(f"/api/v1/sessions/{sid}", json={"title": "x" * 101})
    assert resp.status_code == 422


def test_rename_nonexistent_session_404(client_with_storage: TestClient) -> None:
    resp = client_with_storage.patch(
        f"/api/v1/sessions/{'a' * 32}", json={"title": "new name"},
    )
    assert resp.status_code == 404
