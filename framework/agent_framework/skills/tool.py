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

    # HIGH-1: allowed_skills 是访问控制边界(非仅 prompt 可见性) —
    # 白名单外的 skill 拒绝加载全文,防 LLM 绕过 describe_available 过滤直接 load_skill。
    allowed = ctx.extra.get("allowed_skills")
    if allowed is not None and name not in allowed:
        return ToolResult(content=f"skill '{name}' 不在当前 agent 的允许列表内", is_error=True)

    result = registry.load_full_text(name)
    if result.is_error:
        return ToolResult(content=result.content, is_error=True)

    content = result.content
    if not registry.is_trusted(name):
        content = f"[untrusted] {content}"

    return ToolResult(content=content, is_error=False)


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
