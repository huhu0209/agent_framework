"""PromptAssembler — 将 AgentProfile 组装成 system prompt。"""

from __future__ import annotations

from agent_framework.prompts.profiles import AgentProfile, PromptBlock


class PromptAssembler:
    """将 AgentProfile 的各模块组装成有序的 PromptBlock 列表或 system prompt 字符串。"""

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
        return "\n\n".join(b.content for b in blocks if b.content)
