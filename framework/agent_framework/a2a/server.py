"""A2AServer — pure ASGI app exposing an Agent as HTTP endpoints.

Routes:
  GET  /.well-known/agent-card  → AgentCard JSON
  POST /tasks                   → Create task, background-execute agent
  GET  /tasks/{id}              → Query task status
  POST /tasks/{id}/cancel       → Cancel a task
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from pydantic import SecretStr

from agent_framework.a2a.models import A2ATask, A2ATaskStatus
from agent_framework.agents.base import Agent

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class A2AServer:
    """Pure ASGI application that exposes an Agent via A2A protocol routes."""

    def __init__(
        self,
        agent: Agent,
        agent_card_data: dict[str, Any],
        api_key: str | None = None,
    ) -> None:
        self._agent = agent
        self._agent_card_data = agent_card_data
        self._api_key: SecretStr | None = SecretStr(api_key) if api_key else None
        self._tasks: dict[str, A2ATask] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return

        # Auth gate — check before routing
        auth_ok, error_status = self._verify_auth(scope)
        if not auth_ok:
            message = "Missing API key" if error_status == 401 else "Invalid API key"
            await self._send_json(send, error_status, {"error": message})
            return

        method: str = scope["method"]
        path: str = scope["path"]

        if method == "GET" and path == "/.well-known/agent-card":
            await self._handle_agent_card(scope, receive, send)
        elif method == "POST" and path == "/tasks":
            await self._handle_create_task(scope, receive, send)
        elif method == "GET" and path.startswith("/tasks/"):
            task_id = path[len("/tasks/"):]
            if task_id:
                await self._handle_get_task(task_id, scope, receive, send)
            else:
                await self._send_json(send, 404, {"error": "not found"})
        elif method == "POST" and path.startswith("/tasks/") and path.endswith("/cancel"):
            task_id = path[len("/tasks/") : -len("/cancel")]
            if task_id:
                await self._handle_cancel_task(task_id, scope, receive, send)
            else:
                await self._send_json(send, 404, {"error": "not found"})
        else:
            await self._send_json(send, 404, {"error": "not found"})

    # ── Authentication ────────────────────────────────────────────────────

    def _verify_auth(self, scope: Scope) -> tuple[bool, int]:
        """Check X-API-Key header against configured key.

        Returns (is_ok, status_code_if_not_ok).
        When no api_key is configured, always returns (True, 200).
        """
        if self._api_key is None:
            return True, 200

        expected = self._api_key.get_secret_value()
        headers = scope.get("headers", [])
        for key, value in headers:
            if key == b"x-api-key":
                if value.decode() == expected:
                    return True, 200
                return False, 403

        return False, 401

    # ── Route Handlers ───────────────────────────────────────────────────

    async def _handle_agent_card(
        self, scope: Scope, receive: Receive, send: Send,
    ) -> None:
        await self._send_json(send, 200, self._agent_card_data)

    async def _handle_create_task(
        self, scope: Scope, receive: Receive, send: Send,
    ) -> None:
        body = await self._read_body(receive)
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            await self._send_json(send, 400, {"error": "invalid JSON"})
            return

        message = data.get("message", "")

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        task = A2ATask(
            id=task_id,
            status=A2ATaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        async with self._lock:
            self._tasks[task_id] = task

        asyncio.create_task(self._execute_task(task_id, message))

        await self._send_json(send, 201, task.model_dump())

    async def _handle_get_task(
        self, task_id: str, scope: Scope, receive: Receive, send: Send,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)

        if task is None:
            await self._send_json(send, 404, {"error": "task not found"})
            return

        await self._send_json(send, 200, task.model_dump())

    async def _handle_cancel_task(
        self, task_id: str, scope: Scope, receive: Receive, send: Send,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                await self._send_json(send, 404, {"error": "task not found"})
                return
            if task.status.is_terminal:
                await self._send_json(send, 409, {"error": "task already in terminal state"})
                return
            now = datetime.now(timezone.utc).isoformat()
            updated = task.model_copy(
                update={
                    "status": A2ATaskStatus.CANCELED,
                    "updated_at": now,
                },
            )
            self._tasks[task_id] = updated

        await self._send_json(send, 200, updated.model_dump())

    # ── Background Execution ─────────────────────────────────────────────

    async def _execute_task(self, task_id: str, message: str) -> None:
        try:
            async with self._lock:
                task = self._tasks[task_id]
                self._tasks[task_id] = task.model_copy(
                    update={
                        "status": A2ATaskStatus.RUNNING,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            result_parts: list[str] = []
            async for event in self._agent.run(message):
                if event.type == "done" and "text" in event.data:
                    result_parts.append(event.data["text"])

            async with self._lock:
                task = self._tasks[task_id]
                self._tasks[task_id] = task.model_copy(
                    update={
                        "status": A2ATaskStatus.COMPLETED,
                        "result": "\n".join(result_parts) if result_parts else "",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception as e:
            async with self._lock:
                task = self._tasks.get(task_id)
                if task is not None:
                    self._tasks[task_id] = task.model_copy(
                        update={
                            "status": A2ATaskStatus.FAILED,
                            "error": str(e),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )

    # ── ASGI Helpers ─────────────────────────────────────────────────────

    async def _read_body(self, receive: Receive) -> bytes:
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        return body

    async def _send_json(self, send: Send, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            },
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            },
        )
