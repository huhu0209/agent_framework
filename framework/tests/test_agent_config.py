"""Agent 配置化测试 — parse_agent_config, load_agent_configs, agent_from_config。"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from agent_framework.agents.base import Agent
from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.agents.config import (
    AgentConfig,
    agent_from_config,
    load_agent_configs,
    parse_agent_config,
)
from agent_framework.llm.base import ILLMAdapter
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolSpec, ToolUseContext

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "agents"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_registry_with_tools(*names: str) -> ToolRegistry:
    """创建包含命名工具的 ToolRegistry。"""
    from agent_framework.llm.types import ToolParameterSchema

    registry = ToolRegistry()
    for name in names:
        registry.register(ToolSpec(
            name=name,
            description=f"mock tool {name}",
            parameters=ToolParameterSchema(type="object", properties={}, required=[]),
            handler=AsyncMock(),
        ))
    return registry


def _make_router(registry: ToolRegistry) -> ToolRouter:
    return ToolRouter(registry=registry)


def _make_ctx() -> ToolUseContext:
    return ToolUseContext()


def _make_adapter() -> ILLMAdapter:
    return AsyncMock(spec=ILLMAdapter)


# ---------------------------------------------------------------------------
# parse_agent_config
# ---------------------------------------------------------------------------

class TestParseAgentConfig:
    def test_parse_full(self):
        text = (
            "---\n"
            "name: research-agent\n"
            "description: 研究分析助手\n"
            "model: claude-sonnet-4-6-20250514\n"
            "max_steps: 15\n"
            "tools: read_file, web_search\n"
            "---\n"
            "你是一个专业的分析师，擅长搜索和整理信息。\n"
        )
        config = parse_agent_config(text, filename="research-agent.md")

        assert config.name == "research-agent"
        assert config.description == "研究分析助手"
        assert config.model == "claude-sonnet-4-6-20250514"
        assert config.max_steps == 15
        assert config.tools == ["read_file", "web_search"]
        assert "专业的分析师" in config.system_prompt

    def test_parse_minimal(self):
        text = "---\nname: minimal-agent\n---\n你是一个简单的助手。\n"
        config = parse_agent_config(text, filename="minimal-agent.md")

        assert config.name == "minimal-agent"
        assert config.model == "claude-sonnet-4-6-20250514"
        assert config.max_steps == 10
        assert config.tools is None
        assert config.description == ""
        assert config.system_prompt == "你是一个简单的助手。"

    def test_missing_name_raises(self):
        text = "---\ndescription: no name\n---\n内容\n"
        with pytest.raises(ValueError, match="缺少 name"):
            parse_agent_config(text)

    def test_empty_system_prompt_raises(self):
        text = "---\nname: test\n---\n"
        with pytest.raises(ValueError, match="system_prompt 不能为空"):
            parse_agent_config(text)

    def test_tools_with_spaces(self):
        text = "---\nname: spaced\n---\n助手\n"
        config = parse_agent_config(text)
        assert config.tools is None

    def test_tools_single(self):
        text = "---\nname: single\n---\n助手\n"
        config = parse_agent_config(text)
        assert config.tools is None


# ---------------------------------------------------------------------------
# load_agent_configs
# ---------------------------------------------------------------------------

class TestLoadAgentConfigs:
    def test_from_directory(self):
        configs = load_agent_configs(FIXTURES_DIR)

        assert "research-agent" in configs
        assert "minimal-agent" in configs
        assert configs["research-agent"].max_steps == 15
        assert configs["minimal-agent"].max_steps == 10

    def test_duplicate_names_raises(self, tmp_path):
        content = "---\nname: dup\n---\n助手A\n"
        (tmp_path / "a.md").write_text(content, encoding="utf-8")
        (tmp_path / "b.md").write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="重复的 Agent name"):
            load_agent_configs(tmp_path)

    def test_empty_directory(self, tmp_path):
        configs = load_agent_configs(tmp_path)
        assert configs == {}


# ---------------------------------------------------------------------------
# agent_from_config
# ---------------------------------------------------------------------------

class TestAgentFromConfig:
    def test_with_tool_filter(self):
        registry = _make_registry_with_tools("read_file", "web_search", "write_file")
        router = _make_router(registry)
        config = AgentConfig(
            name="filtered",
            system_prompt="test",
            tools=["read_file", "web_search"],
        )
        agent = agent_from_config(config, _make_adapter(), router, _make_ctx())

        assert isinstance(agent, AgentLoop)
        assert sorted(agent.router.registry.list_tools()) == ["read_file", "web_search"]

    def test_all_tools(self):
        registry = _make_registry_with_tools("read_file", "web_search", "write_file")
        router = _make_router(registry)
        config = AgentConfig(name="all", system_prompt="test", tools=None)
        agent = agent_from_config(config, _make_adapter(), router, _make_ctx())

        assert isinstance(agent, AgentLoop)
        assert agent.router.registry.list_tools() == ["read_file", "web_search", "write_file"]

    def test_is_agent_loop_and_agent(self):
        registry = _make_registry_with_tools("read_file")
        router = _make_router(registry)
        config = AgentConfig(name="test", system_prompt="test")
        agent = agent_from_config(config, _make_adapter(), router, _make_ctx())

        assert isinstance(agent, AgentLoop)
        assert isinstance(agent, Agent)

    def test_config_fields_propagate(self):
        registry = _make_registry_with_tools("read_file")
        router = _make_router(registry)
        config = AgentConfig(
            name="custom",
            system_prompt="custom prompt",
            model="claude-haiku-4-5-20250514",
            max_steps=5,
        )
        agent = agent_from_config(config, _make_adapter(), router, _make_ctx())

        assert agent.model == "claude-haiku-4-5-20250514"
        assert agent.max_steps == 5
        assert agent._system_prompt_text == "custom prompt"
