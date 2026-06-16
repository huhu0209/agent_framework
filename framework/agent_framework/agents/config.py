"""Agent 配置化 — 从 .md 文件声明式定义 Agent。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.config.loader import ConfigLoader
from agent_framework.llm.base import ILLMAdapter
from agent_framework.memory.frontmatter import parse_frontmatter
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)

# Agent 默认模型（当前与 anthropic_provider.ANTHROPIC_DEFAULT_MODEL 一致）
_DEFAULT_MODEL = "claude-sonnet-4-6-20250514"


@dataclass
class AgentConfig:
    """Agent 配置，从 .md frontmatter + body 解析而来。"""

    name: str
    system_prompt: str
    description: str = ""
    model: str = _DEFAULT_MODEL
    max_steps: int = 10
    tools: list[str] | None = None

    @classmethod
    def from_loader(cls, loader: ConfigLoader) -> dict[str, AgentConfig]:
        """从 ConfigLoader 的多目录扫描加载所有 Agent 配置。

        按 discover() 自然顺序 [global, project] 迭代，project 后写入
        覆盖 global。名称冲突时记录 warning。
        """
        paths = loader.discover("agents")
        result: dict[str, AgentConfig] = {}
        for path in paths:
            for name, config in load_agent_configs(path).items():
                if name in result:
                    logger.warning(
                        "Agent '%s' from %s overrides global", name, path,
                    )
                result[name] = config
        return result


def _extract_body(text: str) -> str:
    """从 frontmatter 文档中提取 body（第二个 --- 之后的内容）。"""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    return parts[2].strip()


def parse_agent_config(text: str, filename: str = "<unknown>") -> AgentConfig:
    """解析单个 .md 文件为 AgentConfig。

    frontmatter 提供 name/description/model/max_steps/tools，
    body 作为 system_prompt。
    """
    meta = parse_frontmatter(text)

    name = meta.get("name")
    if not name:
        raise ValueError(f"Agent 配置缺少 name 字段: {filename}")

    model = meta.get("model", _DEFAULT_MODEL)
    max_steps = int(meta.get("max_steps", "10"))
    description = meta.get("description", "")

    tools_raw = meta.get("tools", "")
    tools = [t.strip() for t in tools_raw.split(",") if t.strip()] if tools_raw else None

    system_prompt = _extract_body(text)
    if not system_prompt:
        raise ValueError(f"Agent 配置 system_prompt 不能为空: {filename}")

    return AgentConfig(
        name=name,
        system_prompt=system_prompt,
        description=description,
        model=model,
        max_steps=max_steps,
        tools=tools,
    )


def load_agent_configs(directory: Path) -> dict[str, AgentConfig]:
    """扫描目录中所有 .md 文件，解析为 AgentConfig dict。"""
    configs: dict[str, AgentConfig] = {}

    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        config = parse_agent_config(text, filename=path.name)

        if config.name in configs:
            raise ValueError(f"重复的 Agent name: {config.name}")

        configs[config.name] = config

    return configs


def agent_from_config(
    config: AgentConfig,
    adapter: ILLMAdapter,
    router: ToolRouter,
    ctx: ToolUseContext,
) -> AgentLoop:
    """根据 AgentConfig 创建 AgentLoop 实例，支持工具过滤。"""
    if config.tools is not None:
        filtered_router = router.derive(router.registry.subset(set(config.tools)))
    else:
        filtered_router = router

    return AgentLoop(
        adapter=adapter,
        model=config.model,
        router=filtered_router,
        ctx=ctx,
        max_steps=config.max_steps,
        system_prompt=config.system_prompt,
    )
