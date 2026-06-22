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
