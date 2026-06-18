"""Tests for A2AClient — HTTP calls, polling, timeout, ToolSpec registration."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from agent_framework.a2a.client import A2AClient
from agent_framework.a2a.models import A2ATask, A2ATaskStatus, AgentCard
from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolResult, ToolUseContext


# ── Helpers ──────────────────────────────────────────────────────────────────


SAMPLE_CARD = AgentCard(
    name="remote-agent",
    description="A remote agent for testing",
    url="http://localhost:9999",
)

SAMPLE_TASK_DICT: dict[str, Any] = {
    "id": "task-123",
    "status": "pending",
    "result": None,
    "error": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}

COMPLETED_TASK_DICT: dict[str, Any] = {
    "id": "task-123",
    "status": "completed",
    "result": "final answer",
    "error": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:01+00:00",
}

CANCELED_TASK_DICT: dict[str, Any] = {
    "id": "task-123",
    "status": "canceled",
    "result": None,
    "error": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:01+00:00",
}

FAILED_TASK_DICT: dict[str, Any] = {
    "id": "task-123",
    "status": "failed",
    "result": None,
    "error": "something went wrong",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:01+00:00",
}


def make_client(
    handler: httpx.MockTransport | None = None,
) -> A2AClient:
    if handler is None:
        handler = httpx.MockTransport(lambda req: httpx.Response(200))
    transport = handler
    client = A2AClient(agent_card=SAMPLE_CARD)
    # Replace internal httpx client with mock transport
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url=SAMPLE_CARD.url,
        headers={"Content-Type": "application/json"},
    )
    return client


def json_response(data: dict[str, Any], status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


# ── Constructor ──────────────────────────────────────────────────────────────


class TestConstructor:
    def test_creates_client_with_card(self) -> None:
        client = A2AClient(agent_card=SAMPLE_CARD)
        assert client._agent_card.name == "remote-agent"

    def test_creates_client_with_api_key(self) -> None:
        client = A2AClient(agent_card=SAMPLE_CARD, api_key="secret123")
        assert client._api_key is not None


# ── send_task ────────────────────────────────────────────────────────────────


class TestSendTask:
    @pytest.mark.asyncio
    async def test_send_task_returns_task_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert request.url.path == "/tasks"
            body = json.loads(request.content)
            assert body["message"] == "hello"
            return json_response({"id": "task-abc", "status": "pending",
                                  "result": None, "error": None,
                                  "created_at": "...", "updated_at": "..."}, 201)

        client = make_client(httpx.MockTransport(handler))
        task_id = await client.send_task("hello")
        assert task_id == "task-abc"

    @pytest.mark.asyncio
    async def test_send_task_http_error_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = make_client(httpx.MockTransport(handler))
        with pytest.raises(httpx.HTTPStatusError):
            await client.send_task("hello")


# ── get_task ─────────────────────────────────────────────────────────────────


class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task_returns_a2a_task(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return json_response(COMPLETED_TASK_DICT)

        client = make_client(httpx.MockTransport(handler))
        task = await client.get_task("task-123")
        assert isinstance(task, A2ATask)
        assert task.id == "task-123"
        assert task.status == A2ATaskStatus.COMPLETED
        assert task.result == "final answer"

    @pytest.mark.asyncio
    async def test_get_task_not_found_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "not found"})

        client = make_client(httpx.MockTransport(handler))
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_task("nonexistent")


# ── cancel_task ──────────────────────────────────────────────────────────────


class TestCancelTask:
    @pytest.mark.asyncio
    async def test_cancel_task_returns_canceled(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert request.url.path == "/tasks/task-123/cancel"
            return json_response(CANCELED_TASK_DICT)

        client = make_client(httpx.MockTransport(handler))
        task = await client.cancel_task("task-123")
        assert task.status == A2ATaskStatus.CANCELED


# ── send_task_and_wait ───────────────────────────────────────────────────────


class TestSendTaskAndWait:
    @pytest.mark.asyncio
    async def test_polls_until_completed(self) -> None:
        call_count = [0]

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return json_response({"id": "task-123", "status": "pending",
                                      "result": None, "error": None,
                                      "created_at": "...", "updated_at": "..."}, 201)
            # GET poll
            call_count[0] += 1
            if call_count[0] < 3:
                return json_response(SAMPLE_TASK_DICT)  # pending
            return json_response(COMPLETED_TASK_DICT)  # completed

        client = make_client(httpx.MockTransport(handler))
        task = await client.send_task_and_wait("hello", poll_interval=0.01, timeout=5.0)
        assert task.status == A2ATaskStatus.COMPLETED
        assert task.result == "final answer"

    @pytest.mark.asyncio
    async def test_timeout_returns_failed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return json_response({"id": "task-123", "status": "pending",
                                      "result": None, "error": None,
                                      "created_at": "...", "updated_at": "..."}, 201)
            # Always return pending (never completes)
            return json_response(SAMPLE_TASK_DICT)

        client = make_client(httpx.MockTransport(handler))
        task = await client.send_task_and_wait("hello", poll_interval=0.01, timeout=0.05)
        assert task.status == A2ATaskStatus.FAILED
        assert "超时" in task.error

    @pytest.mark.asyncio
    async def test_failed_task_stops_polling(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return json_response({"id": "task-123", "status": "pending",
                                      "result": None, "error": None,
                                      "created_at": "...", "updated_at": "..."}, 201)
            return json_response(FAILED_TASK_DICT)

        client = make_client(httpx.MockTransport(handler))
        task = await client.send_task_and_wait("hello", poll_interval=0.01, timeout=5.0)
        assert task.status == A2ATaskStatus.FAILED
        assert task.error == "something went wrong"


# ── register_as_tool ─────────────────────────────────────────────────────────


class TestRegisterAsTool:
    def test_registers_tool_spec_to_registry(self) -> None:
        client = A2AClient(agent_card=SAMPLE_CARD)
        registry = ToolRegistry()
        client.register_as_tool(registry)

        spec = registry.get("a2a__remote-agent")
        assert spec is not None
        assert spec.name == "a2a__remote-agent"
        assert spec.description == "A remote agent for testing"
        assert "message" in spec.parameters.properties
        assert spec.parameters.required == ["message"]
        assert spec.handler is not None

    def test_tool_spec_has_correct_parameters(self) -> None:
        client = A2AClient(agent_card=SAMPLE_CARD)
        registry = ToolRegistry()
        client.register_as_tool(registry)

        spec = registry.get("a2a__remote-agent")
        assert spec is not None
        msg_param = spec.parameters.properties["message"]
        assert msg_param["type"] == "string"


# ── _handle_tool_call ────────────────────────────────────────────────────────


class TestHandleToolCall:
    @pytest.mark.asyncio
    async def test_successful_task_returns_tool_result(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return json_response({"id": "task-123", "status": "pending",
                                      "result": None, "error": None,
                                      "created_at": "...", "updated_at": "..."}, 201)
            return json_response(COMPLETED_TASK_DICT)

        client = make_client(httpx.MockTransport(handler))
        registry = ToolRegistry()
        client.register_as_tool(registry)

        spec = registry.get("a2a__remote-agent")
        assert spec is not None
        ctx = ToolUseContext()
        result = await spec.handler({"message": "hello"}, ctx)
        assert isinstance(result, ToolResult)
        assert result.content == "final answer"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_failed_task_returns_error_tool_result(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return json_response({"id": "task-123", "status": "pending",
                                      "result": None, "error": None,
                                      "created_at": "...", "updated_at": "..."}, 201)
            return json_response(FAILED_TASK_DICT)

        client = make_client(httpx.MockTransport(handler))
        registry = ToolRegistry()
        client.register_as_tool(registry)

        spec = registry.get("a2a__remote-agent")
        assert spec is not None
        ctx = ToolUseContext()
        result = await spec.handler({"message": "hello"}, ctx)
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "something went wrong" in result.content

    @pytest.mark.asyncio
    async def test_http_error_returns_error_tool_result(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Server Error")

        client = make_client(httpx.MockTransport(handler))
        registry = ToolRegistry()
        client.register_as_tool(registry)

        spec = registry.get("a2a__remote-agent")
        assert spec is not None
        ctx = ToolUseContext()
        result = await spec.handler({"message": "hello"}, ctx)
        assert isinstance(result, ToolResult)
        assert result.is_error

    @pytest.mark.asyncio
    async def test_missing_message_returns_friendly_error(self) -> None:
        """H-G3: 缺 message 参数返回友好错误，而非 KeyError str（"'message'"）回灌 LLM。"""
        client = make_client()  # handler 不会被调用（校验在前）
        registry = ToolRegistry()
        client.register_as_tool(registry)

        spec = registry.get("a2a__remote-agent")
        assert spec is not None
        ctx = ToolUseContext()
        result = await spec.handler({}, ctx)  # 缺 message
        assert isinstance(result, ToolResult)
        assert result.is_error is True
        assert "message" in result.content
        assert "'message'" not in result.content  # 非 KeyError str


# ── API-Key Authentication ────────────────────────────────────────────────────


class TestClientApiKey:
    """Tests for A2AClient API-key authentication header."""

    @pytest.mark.asyncio
    async def test_client_sends_api_key_header(self) -> None:
        """Client with api_key sends X-API-Key header in requests."""
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(
                {k.decode().lower() if isinstance(k, bytes) else k.lower(): v.decode() if isinstance(v, bytes) else v
                 for k, v in request.headers.multi_items()},
            )
            return json_response(COMPLETED_TASK_DICT)

        client = A2AClient(agent_card=SAMPLE_CARD, api_key="test-key")
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=SAMPLE_CARD.url,
            headers=client._build_headers(),
        )
        await client.get_task("task-123")
        assert "x-api-key" in captured_headers
        assert captured_headers["x-api-key"] == "test-key"

    @pytest.mark.asyncio
    async def test_client_no_api_key_no_header(self) -> None:
        """Client without api_key does not send X-API-Key header."""
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(
                {k.decode().lower() if isinstance(k, bytes) else k.lower(): v.decode() if isinstance(v, bytes) else v
                 for k, v in request.headers.multi_items()},
            )
            return json_response(COMPLETED_TASK_DICT)

        client = A2AClient(agent_card=SAMPLE_CARD)
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=SAMPLE_CARD.url,
            headers=client._build_headers(),
        )
        await client.get_task("task-123")
        assert "x-api-key" not in captured_headers

    def test_api_key_stored_as_secretstr(self) -> None:
        """API key is stored as SecretStr, not plain string."""
        client = A2AClient(agent_card=SAMPLE_CARD, api_key="my-secret")
        assert client._api_key is not None
        assert "my-secret" not in repr(client._api_key)

    def test_no_api_key_stored_as_none(self) -> None:
        """No API key means _api_key is None."""
        client = A2AClient(agent_card=SAMPLE_CARD)
        assert client._api_key is None
