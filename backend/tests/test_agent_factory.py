"""AgentFactory 测试 — 确认 llm_max_context 从 Settings 透传到 create_adapter。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from agent_framework.llm.resilient import ResilientLLMAdapter

from app.config import Settings
from app.services import agent_factory


def _make_settings(**overrides) -> Settings:
    base: dict = {"llm_api_key": "test-key", "api_key": "test-key"}
    base.update(overrides)
    return Settings(**base)


def _patch_create_adapter(monkeypatch: pytest.MonkeyPatch) -> dict:
    """替换 agent_factory.create_adapter，捕获调用 kwargs，返回 mock adapter。"""
    captured: dict = {}

    def fake_create_adapter(**kwargs):
        captured.update(kwargs)
        return MagicMock(spec=ResilientLLMAdapter)

    monkeypatch.setattr(agent_factory, "create_adapter", fake_create_adapter)
    return captured


def test_from_settings_passes_max_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings.llm_max_context 设值时，透传给 create_adapter(max_context_tokens=...)。"""
    captured = _patch_create_adapter(monkeypatch)

    settings = _make_settings(
        llm_provider="openai",
        llm_model="deepseek-v4-flash",
        llm_max_context=128000,
    )
    agent_factory.AgentFactory.from_settings(settings)

    assert captured["max_context_tokens"] == 128000


def test_from_settings_defaults_max_context_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """未设 llm_max_context 时，传 None（走 provider 默认值）。"""
    captured = _patch_create_adapter(monkeypatch)

    settings = _make_settings(llm_provider="openai", llm_model="deepseek-v4-flash")
    agent_factory.AgentFactory.from_settings(settings)

    assert captured["max_context_tokens"] is None


# --- create_loop(working_dir=...) — project-scoped sessions (T5) ---


def _make_factory(monkeypatch: pytest.MonkeyPatch, storage_dir: Path | None = None) -> agent_factory.AgentFactory:
    """构造最小可用 AgentFactory，adapter 用 mock。"""
    captured = _patch_create_adapter(monkeypatch)
    settings = _make_settings(llm_provider="openai", llm_model="deepseek-v4-flash")
    agent_factory.AgentFactory.from_settings(settings)
    return agent_factory.AgentFactory(
        adapter=mock_adapter(),
        model=settings.llm_model,
        storage_dir=storage_dir,
    )


def mock_adapter() -> MagicMock:
    return MagicMock(spec=ResilientLLMAdapter)


def test_create_loop_uses_working_dir_when_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式传 working_dir 时，ctx.working_dir 应等于传入值。"""
    factory = _make_factory(monkeypatch)

    loop = factory.create_loop(working_dir="/tmp/proj")

    assert loop.ctx.working_dir == "/tmp/proj"


def test_create_loop_working_dir_defaults_to_shared_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """未传 working_dir 但 storage_dir 已设时，默认回退到 shared_workspace。"""
    storage_dir = tmp_path / "sessions"
    factory = _make_factory(monkeypatch, storage_dir=storage_dir)

    loop = factory.create_loop()

    assert loop.ctx.working_dir == str(storage_dir / "shared_workspace")


def test_create_loop_working_dir_overrides_storage_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """显式 working_dir 优先于 storage_dir/shared_workspace 默认。"""
    storage_dir = tmp_path / "sessions"
    factory = _make_factory(monkeypatch, storage_dir=storage_dir)

    loop = factory.create_loop(working_dir="/tmp/override")

    assert loop.ctx.working_dir == "/tmp/override"


def test_create_loop_no_working_dir_no_storage_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """既无 working_dir 也无 storage_dir 时，ctx.working_dir 保持 ToolUseContext 默认（.）。"""
    factory = _make_factory(monkeypatch)  # storage_dir=None

    loop = factory.create_loop()

    assert loop.ctx.working_dir == "."
