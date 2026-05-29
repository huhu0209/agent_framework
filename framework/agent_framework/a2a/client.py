"""A2AClient — HTTP client for calling remote A2A agents.

Two-level API:
  - Low-level: send_task(), get_task(), cancel_task()
  - High-level: send_task_and_wait() with polling + timeout

ToolSpec registration via register_as_tool() lets Agents call remote agents
through the standard ToolRegistry dispatch.
"""

from __future__ import annotations

import asyncio
import time

import httpx
from pydantic import SecretStr

from agent_framework.a2a.models import A2ATask, A2ATaskStatus, AgentCard
from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext


class A2AClient:
    """HTTP client for interacting with a remote A2A agent."""

    def __init__(
        self,
        agent_card: AgentCard,
        api_key: str | None = None,
    ) -> None:
        self._agent_card = agent_card
        self._api_key: SecretStr | None = SecretStr(api_key) if api_key else None
        self._client = httpx.AsyncClient(
            base_url=agent_card.url,
            headers=self._build_headers(),
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=120.0),
        )

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["X-API-Key"] = self._api_key.get_secret_value()
        return headers

    # ── Low-level API ────────────────────────────────────────────────────

    async def send_task(self, message: str) -> str:
        """Submit a task to the remote agent. Returns the task_id."""
        response = await self._client.post("/tasks", json={"message": message})
        response.raise_for_status()
        return response.json()["id"]

    async def get_task(self, task_id: str) -> A2ATask:
        """Query the current state of a remote task."""
        response = await self._client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return A2ATask.model_validate(response.json())

    async def cancel_task(self, task_id: str) -> A2ATask:
        """Request cancellation of a remote task."""
        response = await self._client.post(f"/tasks/{task_id}/cancel")
        response.raise_for_status()
        return A2ATask.model_validate(response.json())

    # ── High-level API ───────────────────────────────────────────────────

    async def send_task_and_wait(
        self,
        message: str,
        *,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> A2ATask:
        """Submit a task and poll until terminal state or timeout."""
        task_id = await self.send_task(message)
        deadline = time.monotonic() + timeout
        last_task: A2ATask | None = None

        while time.monotonic() < deadline:
            task = await self.get_task(task_id)
            last_task = task
            if task.status.is_terminal:
                return task
            await asyncio.sleep(poll_interval)

        # Timeout reached
        now_iso = last_task.updated_at if last_task else ""
        return A2ATask(
            id=task_id,
            status=A2ATaskStatus.FAILED,
            error=f"超时 ({timeout}s)",
            created_at=last_task.created_at if last_task else "",
            updated_at=now_iso,
        )

    # ── ToolSpec Registration ────────────────────────────────────────────

    def register_as_tool(self, registry: ToolRegistry) -> None:
        """Register this client as a ToolSpec so Agents can call the remote agent."""
        spec = ToolSpec(
            name=f"a2a__{self._agent_card.name}",
            description=self._agent_card.description,
            parameters=ToolParameterSchema(
                type="object",
                properties={
                    "message": {
                        "type": "string",
                        "description": "Task description to send to the remote agent",
                    },
                },
                required=["message"],
            ),
            handler=self._handle_tool_call,
        )
        registry.register(spec)

    async def _handle_tool_call(
        self, args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        """ToolSpec handler — calls send_task_and_wait, returns ToolResult."""
        try:
            task = await self.send_task_and_wait(args["message"])
            if task.status == A2ATaskStatus.COMPLETED:
                return ToolResult(content=task.result or "")
            return ToolResult(
                content=task.error or "unknown error",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(content=str(e), is_error=True)

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient."""
        await self._client.aclose()
