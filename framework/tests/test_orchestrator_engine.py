"""Tests for OrchestratorEngine — coordinator Agent Loop."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_framework.orchestrator.engine import OrchestratorEngine
from agent_framework.orchestrator.models import WorkerSpec
from agent_framework.orchestrator.worker_registry import WorkerRegistry
from agent_framework.agents.base import AgentEvent
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


def _make_registry():
    reg = WorkerRegistry()
    reg.register(WorkerSpec(
        name="researcher",
        description="研究代码库",
        factory=MagicMock(),
    ))
    return reg


def _make_engine(registry=None):
    tool_registry = ToolRegistry()
    router = ToolRouter(tool_registry)
    ctx = ToolUseContext()
    return OrchestratorEngine(
        adapter=MagicMock(),
        model="test-model",
        router=router,
        ctx=ctx,
        worker_registry=registry or _make_registry(),
    )


class TestOrchestratorEngineInit:
    def test_creates_with_registry(self):
        engine = _make_engine()
        assert engine._worker_registry is not None

    def test_requires_worker_registry(self):
        with pytest.raises(ValueError):
            OrchestratorEngine(
                adapter=MagicMock(), model="test", router=MagicMock(), ctx=MagicMock(),
                worker_registry=None,
            )


class TestOrchestratorEngineEvents:
    @pytest.mark.asyncio
    async def test_run_yields_events(self):
        engine = _make_engine()

        with patch("agent_framework.agents.agent_loop.AgentLoop") as MockLoop:
            mock_instance = MagicMock()
            async def fake_run(msg, **kwargs):
                yield AgentEvent(type="done", step=1, data={
                    "content": [{"type": "text", "text": "task completed"}],
                })
            mock_instance.run = fake_run
            MockLoop.return_value = mock_instance

            events = []
            async for event in engine.run("do something"):
                events.append(event)

            assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_run_rejects_oversized_message(self):
        engine = _make_engine()
        with pytest.raises(ValueError, match="too long"):
            async for _ in engine.run("x" * 200_000):
                pass
