"""Skills 系统 — load_skill 工具。"""

from __future__ import annotations

from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext


async def _handle_load_skill(args: dict, ctx: ToolUseContext) -> ToolResult:
    """load_skill 工具处理器。"""
    registry = ctx.extra.get("skill_registry")
    if registry is None:
        return ToolResult(content="skill_registry 未配置", is_error=True)

    name = args.get("name", "").strip()
    if not name:
        return ToolResult(content="请指定 skill 名称", is_error=True)

    full_text = registry.load_full_text(name)
    if full_text.startswith("错误："):
        return ToolResult(content=full_text, is_error=True)

    return ToolResult(content=full_text)


def create_load_skill_spec() -> ToolSpec:
    """创建 load_skill 工具的 ToolSpec。"""
    return ToolSpec(
        name="load_skill",
        description=(
            "加载指定 skill 的完整指令正文到当前上下文。"
            "在需要专业领域知识时优先调用。"
            "参数 name 为 skill 名称，"
            "可通过 system prompt 中的 Skills available 列表查看可用 skill。"
        ),
        parameters=ToolParameterSchema(
            properties={
                "name": {
                    "type": "string",
                    "description": "要加载的 skill 名称",
                },
            },
            required=["name"],
        ),
        handler=_handle_load_skill,
        timeout_ms=5_000,
        annotations={"readOnlyHint": True},
    )
