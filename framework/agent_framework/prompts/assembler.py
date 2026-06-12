"""PromptAssembler — 将 AgentProfile + Skills 组装成 system prompt。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework.config.loader import ConfigLoader
from agent_framework.prompts.profiles import AgentProfile, PromptBlock
from agent_framework.rules.loader import RuleLoader

if TYPE_CHECKING:
    from agent_framework.skills.registry import SkillRegistry

_BLOCK_TAGS: dict[str, str] = {
    "USER_PROVIDED": "user-provided",
    "RULES": "rules",
    "SOUL": "soul",
    "AGENTS_RULES": "instructions",
    "IDENTITY": "identity",
    "SKILLS": "skills",
    "TOOL_GUIDANCE": "tool-guidance",
}


class PromptAssembler:
    """将 AgentProfile 的各模块组装成有序的 PromptBlock 列表或 system prompt 字符串。"""

    def __init__(self, skill_registry: SkillRegistry | None = None) -> None:
        self._skill_registry = skill_registry

    def assemble(
        self,
        loader: ConfigLoader,
        profile: AgentProfile,
        context_path: str | None = None,
    ) -> list[PromptBlock]:
        """组装 profile 为 PromptBlock 列表。

        块顺序: USER_PROVIDED -> RULES -> SOUL -> AGENTS_RULES -> IDENTITY -> SKILLS -> TOOL_GUIDANCE
        """
        blocks: list[PromptBlock] = []

        # 1. USER_PROVIDED — 来自 ConfigLoader 的 AGENTS.md 链
        user_content = loader.load_agents_md()
        if user_content:
            blocks.append(PromptBlock(
                name="USER_PROVIDED",
                content=user_content,
                source="auto_generated",
                stability="semi_static",
                cache_breakpoint=True,
            ))

        # 2. RULES — 来自 RuleLoader 的路径过滤规则
        rules_content = RuleLoader.load_rules(loader, context_path)
        if rules_content:
            blocks.append(PromptBlock(
                name="RULES",
                content=rules_content,
                source="auto_generated",
                stability="semi_static",
                cache_breakpoint=True,
            ))

        # 3. SOUL
        if profile.soul:
            blocks.append(PromptBlock(
                name="SOUL",
                content=profile.soul,
                source="injected",
                stability="static",
                cache_breakpoint=True,
            ))

        # 4. AGENTS_RULES
        if profile.agents_rules:
            blocks.append(PromptBlock(
                name="AGENTS_RULES",
                content=profile.agents_rules,
                source="injected",
                stability="static",
                cache_breakpoint=True,
            ))

        # 5. IDENTITY
        if profile.identity:
            blocks.append(PromptBlock(
                name="IDENTITY",
                content=profile.identity,
                source="injected",
                stability="semi_static",
                cache_breakpoint=True,
            ))

        # 6. SKILLS
        if self._skill_registry is not None:
            catalog = self._skill_registry.describe_available()
            blocks.append(PromptBlock(
                name="SKILLS",
                content=f"可用 Skills（按需调用 load_skill 加载完整指令）：\n{catalog}",
                source="auto_generated",
                stability="static",
                cache_breakpoint=False,
            ))

        # 7. TOOL_GUIDANCE
        if profile.tool_guidance:
            blocks.append(PromptBlock(
                name="TOOL_GUIDANCE",
                content=profile.tool_guidance,
                source="injected",
                stability="static",
                cache_breakpoint=False,
            ))

        return blocks

    def render(
        self,
        loader: ConfigLoader,
        profile: AgentProfile,
        context_path: str | None = None,
    ) -> str:
        """将 profile 渲染为完整的 system prompt 字符串。"""
        blocks = self.assemble(loader, profile, context_path)
        parts = []
        for b in blocks:
            if not b.content:
                continue
            tag = _BLOCK_TAGS.get(b.name)
            if tag:
                parts.append(f"<{tag}>\n{b.content}\n</{tag}>")
            else:
                parts.append(b.content)
        return "\n\n".join(parts)
