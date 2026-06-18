"""StubAgentFactory 测试 — 确认 stub loop 产生固定事件序列且元数据接口完整。"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app.services.stub_factory import StubAgentFactory


def test_stub_factory_creates_loop_with_fixed_events() -> None:
    factory = StubAgentFactory()
    loop = factory.create_loop()
    # 元数据接口（AgentRunner.wrap 启动读取）
    assert loop.model == "stub-model"
    assert loop.max_steps == 5
    assert loop.profile is None
    assert isinstance(loop.system_prompt_text, str)
    assert loop.system_prompt_blocks == []
    assert [d.name for d in loop.router.registry.get_definitions()] == ["search", "mcp__weather"]


async def test_stub_loop_yields_fixed_tool_sequence() -> None:
    loop = StubAgentFactory().create_loop()
    events = [e async for e in loop.run("anything")]
    types = [e.type for e in events]
    assert "tool_result" in types
    assert "done" in types
    # 工具调用带固定 id（E2E 可断言）
    tool_result = next(e for e in events if e.type == "tool_result")
    assert tool_result.data["tool_calls"][0]["id"] == "stub_tc_1"


def test_stub_mode_wired_in_lifespan(monkeypatch: pytest.MonkeyPatch) -> None:
    """APP_AGENT_BACKEND=stub 时 lifespan 用 StubAgentFactory。"""
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_WS_ENABLED", "false")
    monkeypatch.setenv("APP_AGENT_BACKEND", "stub")

    from main import app

    with TestClient(app, headers={"X-API-Key": "test-key"}) as client:
        assert isinstance(client.app.state.agent_factory, StubAgentFactory)
        # chat 走 stub，不调真实 LLM
        res = client.post("/api/v1/chat", json={"message": "hi"})
        assert res.status_code == 200
