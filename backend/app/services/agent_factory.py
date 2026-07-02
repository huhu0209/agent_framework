"""Agent 工厂 — 组装 AgentLoop 实例。"""

from __future__ import annotations

import logging
from pathlib import Path

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.commands.dispatcher import CommandDispatcher
from agent_framework.config.loader import ConfigLoader
from agent_framework.hooks.manager import HookManager
from agent_framework.llm import create_adapter
from agent_framework.llm.resilient import ResilientLLMAdapter
from agent_framework.prompts.assembler import PromptAssembler
from agent_framework.prompts.profiles import AgentProfile
from agent_framework.skills.registry import SkillRegistry
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

from app.config import Settings

logger = logging.getLogger(__name__)


class AgentFactory:
    """根据配置创建 AgentLoop 实例，复用无状态组件。"""

    def __init__(self, adapter: ResilientLLMAdapter, model: str, storage_dir: Path | None = None) -> None:
        self._adapter = adapter
        self._model = model
        self._router = ToolRouter(create_builtin_registry())
        self._storage_dir = storage_dir
        # from_configloader() 设置的组件（初始为 None）
        self._loader: ConfigLoader | None = None
        self._skill_registry: SkillRegistry | None = None
        self._hook_manager: HookManager | None = None
        self._command_dispatcher: CommandDispatcher | None = None
        self._default_profile: AgentProfile | None = None
        self._assembler: PromptAssembler | None = None

    @classmethod
    def from_settings(cls, settings: Settings, storage_dir: Path | None = None) -> AgentFactory:
        adapter = create_adapter(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            max_context_tokens=settings.llm_max_context,
        )
        return cls(adapter=adapter, model=settings.llm_model, storage_dir=storage_dir)

    @classmethod
    def from_configloader(cls, loader: ConfigLoader, backend_settings: Settings) -> AgentFactory:
        """单次调用全初始化 — per D-13, D-14。

        从 ConfigLoader 初始化所有模块注册表，创建完整的 AgentFactory。
        backend_settings 用于 LLM adapter 创建（env vars 已为最高优先级 per D-01）。
        """
        # LLM adapter — 使用 backend_settings（env var 已注入）
        adapter = create_adapter(
            provider=backend_settings.llm_provider,
            api_key=backend_settings.llm_api_key.get_secret_value(),
            model=backend_settings.llm_model,
            base_url=backend_settings.llm_base_url,
            max_context_tokens=backend_settings.llm_max_context,
        )
        factory = cls(adapter=adapter, model=backend_settings.llm_model)

        # 存储 loader 引用
        factory._loader = loader

        # 初始化模块注册表 per D-14
        factory._skill_registry = SkillRegistry.from_loader(loader)
        factory._hook_manager = HookManager.from_loader(loader)
        factory._command_dispatcher = CommandDispatcher.from_loader(loader)

        # 加载默认 profile — 不存在时为 None
        factory._default_profile = None
        try:
            factory._default_profile = AgentProfile.from_profile(loader, "default")
        except ValueError:
            logger.info("default profile 不存在，跳过")

        # PromptAssembler with skill registry
        factory._assembler = PromptAssembler(skill_registry=factory._skill_registry)

        return factory

    def create_loop(
        self,
        agent_name: str | None = None,
        working_dir: str | None = None,
    ) -> AgentLoop:
        """创建 AgentLoop 实例。

        agent_name 非空 → 加载该 agent 定义(~/.agent-framework/agents/<名>/),
        用其 AgentProfile + model + skills 名单;为空 → 回退 _default_profile(现状不变)。
        working_dir 显式指定时优先;否则回退 storage_dir/shared_workspace。
        """
        ctx = ToolUseContext()
        if working_dir is not None:
            ctx.working_dir = working_dir
        elif self._storage_dir is not None:
            ctx.working_dir = str(self._storage_dir / "shared_workspace")

        skill_dirs = None
        if self._loader is not None:
            skill_dirs = self._loader.discover("skills")

        # --- agent 选择:具名 agent 优先,否则回退 default profile ---
        profile = self._default_profile
        model = self._model
        allowed_skills: list[str] | None = None

        if agent_name:
            if self._loader is None:
                # LOW#4: agent_name 指定但 loader 未配置 — 与「未找到」语义区分
                logger.warning(
                    "agent '%s' 指定但 loader 未配置,回退 default profile", agent_name,
                )
            else:
                found = False
                from agent_framework.agents.definition import discover_agent_dirs
                for agent_dir in discover_agent_dirs(self._loader):
                    if agent_dir.name == agent_name:
                        from agent_framework.agents.definition import AgentDefinition
                        ad = AgentDefinition.from_directory(agent_dir)
                        profile = ad.profile
                        allowed_skills = ad.skills
                        if ad.model:
                            model = ad.model
                        found = True
                        break
                if not found:  # LOW#3: 用 found 布尔,不依赖 is 副作用判定
                    logger.warning(
                        "agent '%s' 未找到,回退 default profile", agent_name,
                    )

        return AgentLoop(
            adapter=self._adapter,
            model=model,
            router=self._router,
            ctx=ctx,
            profile=profile,
            allowed_skills=allowed_skills,
            hook_manager=self._hook_manager,
            skill_dirs=skill_dirs,
            config_loader=self._loader,
        )
