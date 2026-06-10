"""PromptAssembler — 将 AgentProfile + Skills 组装成 system prompt。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_framework.prompts.profiles import AgentProfile, PromptBlock

if TYPE_CHECKING:
    from agent_framework.skills.registry import SkillRegistry

_BLOCK_TAGS: dict[str, str] = {
    "SOUL": "soul",
    "AGENTS_RULES": "instructions",
    "IDENTITY": "identity",
    "USER": "user-provided",
    "SKILLS": "skills",
    "TOOL_GUIDANCE": "tool-guidance",
}


class PromptAssembler:
    """将 AgentProfile 的各模块组装成有序的 PromptBlock 列表或 system prompt 字符串。"""

    def __init__(self, skill_registry: SkillRegistry | None = None) -> None:
        self._skill_registry = skill_registry

    def assemble(self, profile: AgentProfile) -> list[PromptBlock]:
        """组装 profile 为 PromptBlock 列表。"""
        blocks: list[PromptBlock] = []

        if profile.soul:
            blocks.append(PromptBlock(
                name="SOUL",
                content=profile.soul,
                source="injected",
                stability="static",
                cache_breakpoint=True,
            ))

        if profile.agents_rules:
            blocks.append(PromptBlock(
                name="AGENTS_RULES",
                content=profile.agents_rules,
                source="injected",
                stability="static",
                cache_breakpoint=True,
            ))

        if profile.identity:
            blocks.append(PromptBlock(
                name="IDENTITY",
                content=profile.identity,
                source="injected",
                stability="semi_static",
                cache_breakpoint=True,
            ))

        if profile.user_context:
            blocks.append(PromptBlock(
                name="USER",
                content=profile.user_context,
                source="injected",
                stability="semi_static",
                cache_breakpoint=True,
            ))

        # SKILLS block — 在 TOOL_GUIDANCE 之前
        if self._skill_registry is not None:
            catalog = self._skill_registry.describe_available()
            blocks.append(PromptBlock(
                name="SKILLS",
                content=f"可用 Skills（按需调用 load_skill 加载完整指令）：\n{catalog}",
                source="auto_generated",
                stability="static",
                cache_breakpoint=False,
            ))

        if profile.tool_guidance:
            blocks.append(PromptBlock(
                name="TOOL_GUIDANCE",
                content=profile.tool_guidance,
                source="injected",
                stability="static",
                cache_breakpoint=False,
            ))

        return blocks

    def render(self, profile: AgentProfile) -> str:
        """将 profile 渲染为完整的 system prompt 字符串。"""
        blocks = self.assemble(profile)
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
