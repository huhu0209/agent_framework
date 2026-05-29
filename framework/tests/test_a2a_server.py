"""Tests for A2AServer — pure ASGI app with 4 routes + background agent execution."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

import pytest

from agent_framework.a2a.models import A2ATask, A2ATaskStatus
from agent_framework.a2a.server import A2AServer
from agent_framework.agents.base import Agent, AgentEvent


# ── Helpers ──────────────────────────────────────────────────────────────────


class FakeAgent(Agent):
    """Minimal Agent that yields a few events then a done event."""

    def __init__(
        self,
        events: list[AgentEvent] | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._events = events
        self._raise_error = raise_error

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        if self._raise_error:
            raise self._raise_error
        if self._events:
            for ev in self._events:
                yield ev
        else:
            yield AgentEvent(type="done", step=1, data={"text": f"echo: {user_message}"})


def mock_scope(method: str, path: str) -> dict[str, Any]:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }


def mock_receive(body: bytes | None = None) -> Any:
    """Return a callable that provides ASGI body chunks."""
    chunks = [body or b""]
    call_count = [0]

    async def _receive() -> dict[str, Any]:
        if call_count[0] < len(chunks):
            chunk = chunks[call_count[0]]
            call_count[0] += 1
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": False,
            }
        return {"type": "http.disconnect", "body": b"", "more_body": False}

    return _receive


class MockSend:
    """Collects ASGI send calls and provides parsed response."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        self.calls.append(message)

    def get_response(self) -> tuple[int, dict[str, Any]]:
        """Return (status_code, body_dict) from collected send calls."""
        status = 0
        body_bytes = b""
        for call in self.calls:
            if call["type"] == "http.response.start":
                status = call["status"]
            elif call["type"] == "http.response.body":
                body_bytes += call.get("body", b"")
        return status, json.loads(body_bytes)


SAMPLE_CARD: dict[str, Any] = {
    "name": "test-agent",
    "description": "A test agent",
    "url": "http://localhost:8080",
    "version": "1.0",
    "capabilities": [],
}


def make_server(agent: Agent | None = None) -> A2AServer:
    return A2AServer(agent=agent or FakeAgent(), agent_card_data=SAMPLE_CARD)


# ── Agent Card Route ─────────────────────────────────────────────────────────


class TestAgentCardRoute:
    @pytest.mark.asyncio
    async def test_get_agent_card_returns_200(self) -> None:
        server = make_server()
        send = MockSend()
        await server(mock_scope("GET", "/.well-known/agent-card"), mock_receive(), send)
        status, body = send.get_response()
        assert status == 200
        assert body["name"] == "test-agent"
        assert body["url"] == "http://localhost:8080"


# ── Create Task Route ────────────────────────────────────────────────────────


class TestCreateTaskRoute:
    @pytest.mark.asyncio
    async def test_create_task_returns_201(self) -> None:
        server = make_server()
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        status, resp = send.get_response()
        assert status == 201
        assert resp["status"] == "pending"
        assert "id" in resp
        assert resp["created_at"] == resp["updated_at"]

    @pytest.mark.asyncio
    async def test_create_task_stores_task(self) -> None:
        server = make_server()
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]
        # Task should be in the store
        assert task_id in server._tasks

    @pytest.mark.asyncio
    async def test_create_task_starts_background_execution(self) -> None:
        agent = FakeAgent()
        server = make_server(agent)
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]
        # Give background task time to complete
        await asyncio.sleep(0.1)
        task = server._tasks[task_id]
        assert task.status == A2ATaskStatus.COMPLETED
        assert task.result == "echo: hello"


# ── Get Task Route ───────────────────────────────────────────────────────────


class TestGetTaskRoute:
    @pytest.mark.asyncio
    async def test_get_existing_task_returns_200(self) -> None:
        server = make_server()
        # Create a task first
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]

        # Get the task
        send2 = MockSend()
        await server(mock_scope("GET", f"/tasks/{task_id}"), mock_receive(), send2)
        status, resp2 = send2.get_response()
        assert status == 200
        assert resp2["id"] == task_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_returns_404(self) -> None:
        server = make_server()
        send = MockSend()
        await server(mock_scope("GET", "/tasks/nonexistent-id"), mock_receive(), send)
        status, body = send.get_response()
        assert status == 404
        assert "error" in body


# ── Cancel Task Route ────────────────────────────────────────────────────────


class TestCancelTaskRoute:
    @pytest.mark.asyncio
    async def test_cancel_pending_task_returns_200(self) -> None:
        server = make_server()
        # Create a task
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]

        # Cancel it
        send2 = MockSend()
        await server(mock_scope("POST", f"/tasks/{task_id}/cancel"), mock_receive(), send2)
        status, resp2 = send2.get_response()
        assert status == 200
        assert resp2["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_terminal_task_returns_409(self) -> None:
        # Create a server with an agent that completes instantly
        agent = FakeAgent()
        server = make_server(agent)
        # Create a task and wait for completion
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]
        await asyncio.sleep(0.1)
        # Task should be completed now
        assert server._tasks[task_id].status == A2ATaskStatus.COMPLETED

        # Try to cancel the completed task
        send2 = MockSend()
        await server(mock_scope("POST", f"/tasks/{task_id}/cancel"), mock_receive(), send2)
        status, _ = send2.get_response()
        assert status == 409


# ── Unknown Route ────────────────────────────────────────────────────────────


class TestUnknownRoute:
    @pytest.mark.asyncio
    async def test_unknown_path_returns_404(self) -> None:
        server = make_server()
        send = MockSend()
        await server(mock_scope("GET", "/unknown"), mock_receive(), send)
        status, body = send.get_response()
        assert status == 404

    @pytest.mark.asyncio
    async def test_wrong_method_returns_404(self) -> None:
        server = make_server()
        send = MockSend()
        await server(mock_scope("DELETE", "/tasks"), mock_receive(), send)
        status, _ = send.get_response()
        assert status == 404


# ── Non-HTTP Scope ───────────────────────────────────────────────────────────


class TestNonHttpScope:
    @pytest.mark.asyncio
    async def test_lifespan_scope_is_ignored(self) -> None:
        server = make_server()
        send = MockSend()
        scope = {"type": "lifespan"}
        await server(scope, mock_receive(), send)
        # Should not send any response
        assert len(send.calls) == 0


# ── Background Execution ─────────────────────────────────────────────────────


class TestBackgroundExecution:
    @pytest.mark.asyncio
    async def test_agent_success_sets_completed(self) -> None:
        agent = FakeAgent()
        server = make_server(agent)
        send = MockSend()
        body = json.dumps({"message": "test msg"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]

        await asyncio.sleep(0.1)
        task = server._tasks[task_id]
        assert task.status == A2ATaskStatus.COMPLETED
        assert "test msg" in task.result

    @pytest.mark.asyncio
    async def test_agent_failure_sets_failed(self) -> None:
        agent = FakeAgent(raise_error=RuntimeError("agent crashed"))
        server = make_server(agent)
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]

        await asyncio.sleep(0.1)
        task = server._tasks[task_id]
        assert task.status == A2ATaskStatus.FAILED
        assert "agent crashed" in task.error

    @pytest.mark.asyncio
    async def test_agent_collects_done_text(self) -> None:
        events = [
            AgentEvent(type="thinking", step=1, data={"text": "thinking..."}),
            AgentEvent(type="done", step=2, data={"text": "final answer"}),
        ]
        agent = FakeAgent(events=events)
        server = make_server(agent)
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]

        await asyncio.sleep(0.1)
        task = server._tasks[task_id]
        assert task.status == A2ATaskStatus.COMPLETED
        assert task.result == "final answer"

    @pytest.mark.asyncio
    async def test_status_transitions_from_pending_to_running(self) -> None:
        """Task goes PENDING -> RUNNING during execution."""
        agent = FakeAgent()
        server = make_server(agent)
        send = MockSend()
        body = json.dumps({"message": "hello"}).encode()
        await server(mock_scope("POST", "/tasks"), mock_receive(body), send)
        _, resp = send.get_response()
        task_id = resp["id"]

        # After creation, should be PENDING
        assert server._tasks[task_id].status == A2ATaskStatus.PENDING

        # After execution completes, should be COMPLETED
        await asyncio.sleep(0.1)
        assert server._tasks[task_id].status == A2ATaskStatus.COMPLETED
