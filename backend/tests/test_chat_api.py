"""Chat API 单元测试 — SSE 模式。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
from starlette.testclient import TestClient

from agent_framework.agents.agent_loop import LoopEvent


class _FakeRegistry:
    """假工具注册表 — AgentRunner 读取工具定义列表。"""

    def get_definitions(self) -> list[Any]:
        return []


class _FakeRouter:
    """假 router — 仅暴露 .registry.get_definitions() 供 runner 构造 config。"""

    def __init__(self) -> None:
        self.registry = _FakeRegistry()


class _FakeAgentLoop:
    """产生固定 LoopEvent 序列的假 AgentLoop。"""

    def __init__(self, events: list[LoopEvent]) -> None:
        self._events = events
        self.system_prompt_text = ""  # 匹配 AgentLoop 接口（chat.py TranscriptConsumer 引用）
        # viz AgentRunner.wrap 启动时读取以下元数据（仅在 bus 非 None 时触发）。
        # profile=None → runner 发布 profile/permission_mode=None；其余给最小可用值。
        self.model = "fake-model"
        self.max_steps = 0
        self.profile = None
        self.system_prompt_blocks = []
        self.router = _FakeRouter()

    def effective_context_window(self) -> int:
        """匹配 AgentLoop 接口 — viz AgentRunner.wrap 启动时读取（Inspector 用量指标）。"""
        return 200000

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
        self.last_working_dir: str | None = None

    def create_loop(self, working_dir: str | None = None, agent_name: str | None = None) -> _FakeAgentLoop:
        self.last_working_dir = working_dir
        return _FakeAgentLoop(self._events)


class _FailingFactory:
    def create_loop(self, working_dir: str | None = None, agent_name: str | None = None) -> _FailingAgentLoop:
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
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")

    from app.config import Settings
    from app.services.session import SessionManager
    from main import app

    app.state.settings = Settings()
    session_manager = SessionManager()

    app.state.session_manager = session_manager
    app.state.agent_factory = _FakeFactory()

    return TestClient(app, headers={"X-API-Key": "test-key"})


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
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")

    from app.config import Settings
    from app.services.session import SessionManager
    from main import app

    storage_dir = tmp_path / "sessions"
    session_manager = SessionManager(storage_dir=storage_dir)

    app.state.settings = Settings()
    app.state.session_manager = session_manager
    app.state.agent_factory = _FakeFactory()

    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_transcript_file_created_after_chat(client_with_storage: TestClient, tmp_path: Path) -> None:
    from app.services.session import DEFAULT_BUCKET

    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 200
    sid = res.headers["X-Session-Id"]

    transcript_path = tmp_path / "sessions" / DEFAULT_BUCKET / f"{sid}.jsonl"
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
    from app.services.session import DEFAULT_BUCKET

    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    transcript_path = tmp_path / "sessions" / DEFAULT_BUCKET / f"{sid}.jsonl"
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


async def test_get_messages_from_memory(client: TestClient) -> None:
    """get_messages 应从内存中返回消息。"""
    res = client.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    sm = client.app.state.session_manager
    result = await sm.get_messages(sid)
    assert result is not None
    messages, has_more, next_cursor = result
    assert len(messages) >= 1
    assert messages[0]["role"] == "user"
    assert has_more is False
    assert next_cursor is None


async def test_get_messages_from_transcript(client_with_storage: TestClient) -> None:
    """get_messages 应在 session 被回收后从 transcript 恢复消息。"""
    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    sm = client_with_storage.app.state.session_manager
    sm.remove(sid)
    assert sm.get(sid) is None

    result = await sm.get_messages(sid)
    assert result is not None
    messages, _, _ = result
    assert any(m["role"] == "user" for m in messages)


async def test_get_messages_nonexistent(client: TestClient) -> None:
    """get_messages 对不存在的 session 应返回 None。"""
    sm = client.app.state.session_manager
    assert await sm.get_messages("a" * 32) is None


def test_get_history_after_eviction(client_with_storage: TestClient) -> None:
    """GET /chat/{id} 应在 session 被回收后仍能返回历史。"""
    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    sm = client_with_storage.app.state.session_manager
    sm.remove(sid)

    history_res = client_with_storage.get(f"/api/v1/chat/{sid}")
    assert history_res.status_code == 200
    data = history_res.json()
    assert data["session_id"] == sid
    assert any(m["role"] == "user" for m in data["messages"])


async def test_list_sessions_uses_cache(client_with_storage: TestClient) -> None:
    """list_sessions 应使用缓存，第二次调用返回同一对象。"""
    client_with_storage.post("/api/v1/chat", json={"message": "hello"})

    sm = client_with_storage.app.state.session_manager
    first = await sm.list_sessions()
    assert len(first) >= 1

    assert sm._session_list_cache is not None
    second = await sm.list_sessions()
    assert second is first  # same object reference = cache hit


async def test_list_sessions_cache_invalidated_on_create(client_with_storage: TestClient) -> None:
    """创建 session 后对应桶的缓存应失效。"""
    from app.services.session import DEFAULT_BUCKET

    client_with_storage.post("/api/v1/chat", json={"message": "first"})
    sm = client_with_storage.app.state.session_manager
    await sm.list_sessions()

    client_with_storage.post("/api/v1/chat", json={"message": "second"})
    # 按桶缓存：默认桶条目应被清除
    assert DEFAULT_BUCKET not in (sm._session_list_cache or {})


def test_get_history_with_pagination(client_with_storage: TestClient) -> None:
    """GET /chat/{id}?limit=1 应返回 has_more=true 和分页消息。"""
    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    res = client_with_storage.get(f"/api/v1/chat/{sid}?limit=1")
    assert res.status_code == 200
    data = res.json()
    assert "has_more" in data
    assert data["has_more"] is True
    assert len(data["messages"]) == 1


def test_get_history_without_pagination(client_with_storage: TestClient) -> None:
    """不传 limit 时返回全部消息（向后兼容）。"""
    res = client_with_storage.post("/api/v1/chat", json={"message": "hello"})
    sid = res.headers["X-Session-Id"]

    res = client_with_storage.get(f"/api/v1/chat/{sid}")
    assert res.status_code == 200
    data = res.json()
    assert data["has_more"] is False
    assert len(data["messages"]) >= 1


def test_list_sessions_with_preview(client_with_storage: TestClient) -> None:
    """GET /sessions?preview=2 应在每个会话中附带最近2条消息。"""
    res = client_with_storage.post("/api/v1/chat", json={"message": "first"})
    sid = res.headers["X-Session-Id"]
    client_with_storage.post("/api/v1/chat", json={"message": "second"}, headers={"X-Session-Id": sid})

    res = client_with_storage.get("/api/v1/sessions?preview=2")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    session = next(s for s in data if s["session_id"] == sid)
    assert "preview" in session
    assert isinstance(session["preview"], list)
    assert len(session["preview"]) <= 2
    assert "message_count" in session
    assert session["message_count"] >= 2


def test_list_sessions_without_preview(client_with_storage: TestClient) -> None:
    """GET /sessions 不带 preview 时不应返回 preview 字段（向后兼容）。"""
    client_with_storage.post("/api/v1/chat", json={"message": "hello"})

    res = client_with_storage.get("/api/v1/sessions")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "preview" not in data[0]
    assert "message_count" not in data[0]


@pytest.fixture
def client_no_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """不带 X-API-Key 默认头的客户端，用于测试认证拒绝。"""
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")

    from app.config import Settings
    from app.services.session import SessionManager
    from main import app

    app.state.settings = Settings()
    app.state.session_manager = SessionManager()
    app.state.agent_factory = _FakeFactory()

    return TestClient(app)  # 故意不带默认 X-API-Key 头


def test_post_chat_unauthorized_without_api_key(client_no_auth: TestClient) -> None:
    """A1: 无 X-API-Key 头 → 401。"""
    res = client_no_auth.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_post_chat_wrong_api_key_401(client_no_auth: TestClient) -> None:
    """A1: 错误 X-API-Key → 401。"""
    res = client_no_auth.post(
        "/api/v1/chat", json={"message": "hello"}, headers={"X-API-Key": "wrong"},
    )
    assert res.status_code == 401


def test_post_chat_authorized_with_correct_api_key(client_no_auth: TestClient) -> None:
    """A1: 正确 X-API-Key → 200。"""
    res = client_no_auth.post(
        "/api/v1/chat", json={"message": "hello"}, headers={"X-API-Key": "test-key"},
    )
    assert res.status_code == 200


def test_post_chat_error_persisted_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    """H-A3: 异常落盘 content 是脱敏友好消息，不含 str(exc) 内部细节。"""
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")
    from app.config import Settings
    from app.services.session import SessionManager
    from main import app

    app.state.settings = Settings()
    sm = SessionManager()
    app.state.session_manager = sm
    app.state.agent_factory = _FailingFactory()
    client = TestClient(app, headers={"X-API-Key": "test-key"})

    res = client.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 200

    # session 的 error 消息应脱敏
    sessions = list(sm._sessions.values())
    assert len(sessions) == 1
    error_msgs = [m for m in sessions[0].messages if m.get("role") == "error"]
    assert len(error_msgs) == 1
    assert "agent crashed" not in error_msgs[0]["content"]  # H-A3: 不含内部异常
    assert "服务内部错误" in error_msgs[0]["content"]  # 脱敏友好消息


def test_get_history_limit_too_small_returns_422(client: TestClient) -> None:
    """H-A4: limit < 1 → 422。"""
    res = client.get("/api/v1/chat/" + "a" * 32 + "?limit=0")
    assert res.status_code == 422


def test_get_history_limit_too_large_returns_422(client: TestClient) -> None:
    """H-A4: limit > 500 → 422。"""
    res = client.get("/api/v1/chat/" + "a" * 32 + "?limit=99999")
    assert res.status_code == 422


def test_get_history_invalid_before_returns_422(client: TestClient) -> None:
    """H-A4: before 非数字 → 422（非 500）。"""
    res = client.get("/api/v1/chat/" + "a" * 32 + "?before=abc")
    assert res.status_code == 422


def test_list_sessions_pagination(client_with_storage: TestClient) -> None:
    """H-A5: limit/offset 分页。"""
    for i in range(5):
        client_with_storage.post("/api/v1/chat", json={"message": f"msg {i}"})

    res = client_with_storage.get("/api/v1/sessions?limit=2&offset=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2  # H-A5: 分页切片 sessions[1:3]


def test_list_sessions_pagination_offset_beyond(client_with_storage: TestClient) -> None:
    """H-A5: offset 超出范围 → 空列表（非错误）。"""
    for i in range(3):
        client_with_storage.post("/api/v1/chat", json={"message": f"msg {i}"})

    res = client_with_storage.get("/api/v1/sessions?limit=10&offset=100")
    assert res.status_code == 200
    assert res.json() == []  # offset 超出，空


# --- viz 事件层集成（lifespan + bus + SSE）---
#
# 现有 client fixture 返回 TestClient(app) 但未进 with 上下文，lifespan 从不运行，
# app.state.bus 永不创建，chat 走的是 bus=None 降级路径。这里通过 with 上下文真正
# 跑 lifespan（T5：创建 bus / ws_task），再让 chat 走 runner 装配路径（T7）。


def test_viz_lifespan_creates_bus_and_chat_runs_through_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5+T7：lifespan 运行 → app.state.bus 创建 → chat 经 runner.wrap 仍返回正常 SSE。

    关键点：
    - 进 with TestClient(app) 上下文（lifespan 才会跑）
    - APP_WS_ENABLED=false 避免真启 serve_ws 占端口（bus 仍创建，能测 T7 装配）
    - lifespan 会用真实 AgentFactory 覆盖 app.state.agent_factory；进入 with 后
      重新注入 _FakeFactory，使 chat 不调真实 LLM
    - 断言 app.state.bus 非 None（T5）+ SSE 含 done/shutdown（T7 不破坏流）
    """
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_WS_ENABLED", "false")  # 避免 serve_ws 占用 8765 端口

    from main import app

    # 进 with 上下文 → lifespan 运行 → app.state.bus / session_manager / settings 就绪
    with TestClient(app, headers={"X-API-Key": "test-key"}) as client:
        # T5: lifespan 已创建 EventBus
        assert client.app.state.bus is not None

        # lifespan 用真实 AgentFactory 覆盖了 factory；重新注入 fake，避免调真实 LLM。
        # session_manager 保留 lifespan 创建的实例（含 cleanup task）。
        client.app.state.agent_factory = _FakeFactory()

        # T7: chat 请求走 runner.wrap（bus 非 None）后 SSE 仍正常
        res = client.post("/api/v1/chat", json={"message": "hello"})
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert "X-Session-Id" in res.headers

        events = _parse_sse(res.text)
        event_types = [t for t, _ in events]
        assert "done" in event_types
        assert "shutdown" in event_types

        # T7 装配：bus 非 None 时 chat.py 会构造 runner 挂到 session.agent_runner。
        # 从 session_manager 取回该 session 验证 runner 已装配（非降级路径）。
        sid = res.headers["X-Session-Id"]
        session = client.app.state.session_manager.get(sid)
        assert session is not None
        assert session.agent_runner is not None  # T7: runner 装配生效


def test_chat_request_accepts_project_path():
    from app.models import ChatRequest
    req = ChatRequest(message="hi", project_path="/tmp/x")
    assert req.project_path == "/tmp/x"
    req2 = ChatRequest(message="hi")  # 默认 None
    assert req2.project_path is None
    req3 = ChatRequest(message="hi", project_path="   ")  # 空白 → None
    assert req3.project_path is None


def test_post_chat_with_project_path_routes_to_bucket(client, tmp_path, monkeypatch):
    """Task6: POST /chat 带 project_path → 算 bucket + history 落在桶内。"""
    proj = tmp_path / "myproj"
    proj.mkdir()
    from app.services.session import SessionManager, _bucket_for
    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)
    res = client.post("/api/v1/chat", json={"message": "hi", "project_path": str(proj)})
    assert res.status_code == 200
    bucket = _bucket_for(str(proj))
    # 桶目录被创建,history 落在桶内
    assert (tmp_path / bucket / "history.jsonl").exists()


def test_post_chat_project_path_expands_tilde(client, tmp_path, monkeypatch):
    """HIGH 修复: project_path 含 ~ 时 working_dir 必须是展开后的绝对路径。

    旧实现把 req.project_path 原样传给 create_loop(working_dir=...),
    导致 ~/myproj 字面量落到 file_tools 的 Path(ctx.working_dir),~ 不被展开,
    写入会落在 CWD 下字面名为 ~ 的目录。此测试锁定修复。
    """
    from app.services.session import SessionManager

    # 把 HOME 指到 tmp_path,造一个 ~/myproj
    monkeypatch.setenv("HOME", str(tmp_path))
    proj = tmp_path / "myproj"
    proj.mkdir()
    factory = _FakeFactory()
    client.app.state.agent_factory = factory
    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)

    res = client.post("/api/v1/chat", json={"message": "hi", "project_path": "~/myproj"})
    assert res.status_code == 200
    # working_dir 必须是展开后的绝对路径,而非字面 ~/myproj
    assert factory.last_working_dir == str(proj)
    assert "~" not in (factory.last_working_dir or "")


def test_list_sessions_scoped_by_bucket(client, tmp_path):
    """/sessions?bucket= 收窄到指定桶,不影响默认桶列表。"""
    from app.services.session import SessionManager, _bucket_for

    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)
    client.post("/api/v1/chat", json={"message": "a"})  # default_chat
    proj = tmp_path / "p"
    proj.mkdir()
    client.post("/api/v1/chat", json={"message": "b", "project_path": str(proj)})
    b = _bucket_for(str(proj))

    default_only = client.get("/api/v1/sessions?preview=0").json()
    proj_only = client.get(f"/api/v1/sessions?preview=0&bucket={b}").json()

    assert all(s.get("bucket", "default_chat") == "default_chat" for s in default_only)
    assert len(proj_only) == 1
    assert proj_only[0].get("bucket") == b


def test_list_buckets(client, tmp_path):
    """/sessions/buckets 扫描子目录返回桶列表,default_chat 必在内。"""
    from app.services.session import SessionManager

    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)
    client.post("/api/v1/chat", json={"message": "a"})  # creates default_chat/

    res = client.get("/api/v1/sessions/buckets").json()
    names = [x["bucket"] for x in res]
    assert "default_chat" in names


def test_get_history_scoped_by_bucket(client, tmp_path):
    """GET /chat/{sid} 按 bucket 定位历史；错桶应 404。"""
    from app.services.session import SessionManager, _bucket_for

    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)
    proj = tmp_path / "p"
    proj.mkdir()
    res = client.post("/api/v1/chat", json={"message": "hi", "project_path": str(proj)})
    sid = res.headers["X-Session-Id"]
    b = _bucket_for(str(proj))

    hist = client.get(f"/api/v1/chat/{sid}?bucket={b}")
    assert hist.status_code == 200
    assert hist.json()["session_id"] == sid

    # 不传 bucket(默认 default_chat)应找不到该 session(它在项目桶里)
    miss = client.get(f"/api/v1/chat/{sid}")
    assert miss.status_code == 404


def test_delete_session_scoped_by_bucket(client, tmp_path):
    from app.services.session import SessionManager, _bucket_for
    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)
    proj = tmp_path / "p"; proj.mkdir()
    sid = client.post("/api/v1/chat", json={"message": "hi", "project_path": str(proj)}).headers["X-Session-Id"]
    b = _bucket_for(str(proj))
    # 不传 bucket(默认 default_chat)→ 该 session 不在默认桶 → 404
    miss = client.delete(f"/api/v1/sessions/{sid}")
    assert miss.status_code == 404
    # 传对 bucket → 200
    ok = client.delete(f"/api/v1/sessions/{sid}?bucket={b}")
    assert ok.status_code == 200


def test_rename_session_scoped_by_bucket(client, tmp_path):
    from app.services.session import SessionManager, _bucket_for
    client.app.state.session_manager = SessionManager(storage_dir=tmp_path)
    proj = tmp_path / "p"; proj.mkdir()
    sid = client.post("/api/v1/chat", json={"message": "hi", "project_path": str(proj)}).headers["X-Session-Id"]
    b = _bucket_for(str(proj))
    miss = client.patch(f"/api/v1/sessions/{sid}", json={"title": "new"})
    assert miss.status_code == 404
    ok = client.patch(f"/api/v1/sessions/{sid}?bucket={b}", json={"title": "new"})
    assert ok.status_code == 200


def test_bucket_for_returns_bucket_name(client, tmp_path):
    proj = tmp_path / "myapp"; proj.mkdir()
    res = client.get("/api/v1/sessions/bucket-for", params={"project_path": str(proj)})
    assert res.status_code == 200
    body = res.json()
    assert body["bucket"].startswith("myapp_")
    assert body["display_name"] == "myapp"


def test_bucket_for_missing_path_400(client):
    res = client.get("/api/v1/sessions/bucket-for", params={"project_path": "/no/such/xyz"})
    assert res.status_code == 400


def test_bucket_for_no_path_400(client):
    res = client.get("/api/v1/sessions/bucket-for")
    assert res.status_code == 400


def test_chat_request_accepts_agent_name(client: TestClient) -> None:
    """Task6: ChatRequest 接受 agent_name 字段,不报 422。

    本 task 只铺路(模型/Session/stub factory 签名兼容);
    透传到 factory.create_loop 的断言留到 Task 7 chat.py 接线后。
    """
    res = client.post("/api/v1/chat", json={"message": "hi", "agent_name": "reviewer"})
    assert res.status_code == 200


def test_chat_request_model_has_agent_name_field() -> None:
    """Task6: ChatRequest 模型直接构造时 agent_name 可传入且默认 None。"""
    from app.models import ChatRequest
    req = ChatRequest(message="hi", agent_name="reviewer")
    assert req.agent_name == "reviewer"
    req2 = ChatRequest(message="hi")  # 默认 None
    assert req2.agent_name is None


# --- Task 7: agent_name 透传到 factory.create_loop ---


class _CapturingFactory:
    """记录 create_loop 收到的 agent_name(关键字调用,兼容多种参数顺序)。"""

    def __init__(self, events: list[LoopEvent] | None = None) -> None:
        self._events = events or _make_done_events()
        self.last_agent_name = "UNSET"

    def create_loop(self, working_dir: str | None = None, agent_name: str | None = None) -> _FakeAgentLoop:
        self.last_agent_name = agent_name
        return _FakeAgentLoop(self._events)


def test_chat_new_session_passes_agent_name(client: TestClient) -> None:
    """新建会话时,agent_name 透传给 factory.create_loop。"""
    from main import app
    factory = _CapturingFactory()
    app.state.agent_factory = factory

    res = client.post("/api/v1/chat", json={"message": "hi", "agent_name": "reviewer"})
    assert res.status_code == 200
    assert factory.last_agent_name == "reviewer"


def test_chat_resume_passes_agent_name(client: TestClient) -> None:
    """resume 已有 session 时,agent_name 也透传给 factory.create_loop。"""
    from main import app
    factory = _CapturingFactory()
    app.state.agent_factory = factory

    res1 = client.post("/api/v1/chat", json={"message": "first"})
    sid = res1.headers["X-Session-Id"]
    res2 = client.post("/api/v1/chat", json={
        "message": "second", "session_id": sid, "agent_name": "reviewer",
    })
    assert res2.status_code == 200
    assert factory.last_agent_name == "reviewer"


def test_chat_resume_uses_session_agent_when_request_omits(client: TestClient) -> None:
    """resume 时若请求没带 agent_name,回退到内存 session 绑定的 agent(session 级绑定)。

    场景:前端页面刷新后 currentChatAgent 内存丢失、resume 不带 agent_name,
    应使用该 session 绑定的 agent,而非静默回退 default(spec §6.2)。
    """
    from main import app
    factory = _CapturingFactory()
    app.state.agent_factory = factory

    # 先建一个带 agent_name 的 session(进内存)
    res1 = client.post("/api/v1/chat", json={"message": "first", "agent_name": "reviewer"})
    sid = res1.headers["X-Session-Id"]
    # resume 不带 agent_name
    res2 = client.post("/api/v1/chat", json={"message": "second", "session_id": sid})
    assert res2.status_code == 200
    assert factory.last_agent_name == "reviewer"  # 用 session 绑定的 agent


def test_chat_resume_uses_disk_agent_after_eviction(client: TestClient, tmp_path: Path) -> None:
    """M1: 冷恢复 — session 内存淘汰(重启/TTL)后,resume 不带 agent_name,
    应从磁盘 history 恢复 session 绑定的 agent,而非静默回退 default(spec §6.2)。"""
    from main import app
    from app.services.session import SessionManager

    factory = _CapturingFactory()
    app.state.agent_factory = factory
    app.state.session_manager = SessionManager(storage_dir=tmp_path)

    # 建一个绑定 reviewer 的 session(写磁盘 history + transcript)
    res1 = client.post("/api/v1/chat", json={"message": "first", "agent_name": "reviewer"})
    sid = res1.headers["X-Session-Id"]
    # 模拟重启/TTL 淘汰:清空内存,磁盘数据保留
    app.state.session_manager.remove(sid)
    assert sid not in app.state.session_manager._sessions

    # resume 不带 agent_name → 应从磁盘 history 恢复 "reviewer"
    res2 = client.post("/api/v1/chat", json={"message": "second", "session_id": sid})
    assert res2.status_code == 200
    assert factory.last_agent_name == "reviewer"
