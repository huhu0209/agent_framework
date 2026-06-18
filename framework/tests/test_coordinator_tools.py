"""Tests for coordinator tools — spawn_worker, send_message, list_workers."""

import json
import pytest
from unittest.mock import MagicMock

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.orchestrator.models import WorkerSpec
from agent_framework.orchestrator.worker_agent import WorkerManager
from agent_framework.orchestrator.worker_registry import WorkerRegistry
from agent_framework.tools.types import ToolUseContext

from tests.conftest import async_iter


def _done_event(text: str) -> AgentEvent:
    return AgentEvent(type="done", step=1, data={
        "content": [{"type": "text", "text": text}],
    })


def _make_mock_agent(*, output: str = "done") -> MagicMock:
    agent = MagicMock(spec=Agent)
    agent.run = MagicMock(return_value=async_iter([_done_event(output)]))
    return agent


def _make_manager():
    reg = WorkerRegistry()
    reg.register(WorkerSpec(
        name="researcher",
        description="does research",
        factory=lambda *, adapter, model, router, ctx: _make_mock_agent(output="found 3 issues"),
    ))
    return WorkerManager(
        reg,
        adapter=MagicMock(),
        model="test",
        router=MagicMock(),
        ctx=MagicMock(),
    )


class TestSpawnWorkerTool:
    @pytest.mark.asyncio
    async def test_spawn_returns_tool_result(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        spawn_spec = next(s for s in specs if s.name == "spawn_worker")
        ctx = ToolUseContext(extra={"worker_manager": mgr})

        result = await spawn_spec.handler({"worker_name": "researcher", "prompt": "find bugs"}, ctx)
        assert result.is_error is False
        data = json.loads(result.content)
        assert data["status"] == "completed"
        assert "worker_id" in data
        assert "found 3 issues" in data["output"]

    @pytest.mark.asyncio
    async def test_spawn_unknown_worker_returns_error(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        spawn_spec = next(s for s in specs if s.name == "spawn_worker")
        ctx = ToolUseContext(extra={"worker_manager": mgr})

        result = await spawn_spec.handler({"worker_name": "nonexistent", "prompt": "task"}, ctx)
        assert result.is_error is True

    def test_spawn_has_required_params(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        spawn_spec = next(s for s in specs if s.name == "spawn_worker")
        assert "worker_name" in spawn_spec.parameters.required
        assert "prompt" in spawn_spec.parameters.required


class TestSendMessageTool:
    @pytest.mark.asyncio
    async def test_send_message_returns_result(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        spawn_spec = next(s for s in specs if s.name == "spawn_worker")
        send_spec = next(s for s in specs if s.name == "send_message")
        ctx = ToolUseContext(extra={"worker_manager": mgr})

        spawn_result = await spawn_spec.handler({"worker_name": "researcher", "prompt": "initial"}, ctx)
        data = json.loads(spawn_result.content)
        worker_id = data["worker_id"]

        send_result = await send_spec.handler({"worker_id": worker_id, "message": "go deeper"}, ctx)
        assert send_result.is_error is False
        send_data = json.loads(send_result.content)
        assert send_data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_send_message_unknown_worker_returns_error(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        send_spec = next(s for s in specs if s.name == "send_message")
        ctx = ToolUseContext(extra={"worker_manager": mgr})

        result = await send_spec.handler({"worker_id": "w_nonexistent", "message": "hi"}, ctx)
        assert result.is_error is True


class TestListWorkersTool:
    @pytest.mark.asyncio
    async def test_list_empty(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        list_spec = next(s for s in specs if s.name == "list_workers")
        ctx = ToolUseContext(extra={"worker_manager": mgr})

        result = await list_spec.handler({}, ctx)
        assert result.is_error is False
        data = json.loads(result.content)
        assert data["workers"] == []

    @pytest.mark.asyncio
    async def test_list_after_spawn(self):
        from agent_framework.orchestrator.coordinator_tools import create_coordinator_tools
        mgr = _make_manager()
        specs = create_coordinator_tools(mgr)
        spawn_spec = next(s for s in specs if s.name == "spawn_worker")
        list_spec = next(s for s in specs if s.name == "list_workers")
        ctx = ToolUseContext(extra={"worker_manager": mgr})

        await spawn_spec.handler({"worker_name": "researcher", "prompt": "task"}, ctx)
        result = await list_spec.handler({}, ctx)
        data = json.loads(result.content)
        assert len(data["workers"]) == 1
        assert data["workers"][0]["status"] == "completed"


class TestCoordinatorPrompt:
    def test_prompt_contains_worker_descriptions(self):
        from agent_framework.orchestrator.coordinator_prompt import build_coordinator_prompt
        from agent_framework.orchestrator.worker_registry import WorkerRegistry
        from agent_framework.orchestrator.models import WorkerSpec
        from unittest.mock import MagicMock

        reg = WorkerRegistry()
        reg.register(WorkerSpec(name="researcher", description="研究代码库", factory=MagicMock()))
        prompt = build_coordinator_prompt(reg)
        assert "researcher" in prompt
        assert "spawn_worker" in prompt

    def test_prompt_contains_all_tools(self):
        from agent_framework.orchestrator.coordinator_prompt import build_coordinator_prompt
        from agent_framework.orchestrator.worker_registry import WorkerRegistry

        prompt = build_coordinator_prompt(WorkerRegistry())
        assert "spawn_worker" in prompt
        assert "send_message" in prompt
        assert "list_workers" in prompt
