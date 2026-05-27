"""SubAgent — 在隔离上下文中执行一次性子代理。"""

from __future__ import annotations

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import ToolParameterSchema
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext

RECURSIVE_TOOLS = {"run_subagent", "task_create", "spawn_teammate"}


def create_filtered_router(
    parent: ToolRouter,
    allowed: list[str] | None,
) -> ToolRouter:
    if allowed is not None:
        names = set(allowed)
    else:
        names = set(parent.registry.list_tools())
    names -= RECURSIVE_TOOLS
    return parent.derive(parent.registry.subset(names))


async def run_subagent(
    prompt: str,
    *,
    parent_router: ToolRouter,
    adapter: ILLMAdapter,
    model: str,
    ctx: ToolUseContext,
    system_prompt: str = "你是一个子代理。完成任务后总结你的发现。",
    allowed_tools: list[str] | None = None,
    max_steps: int = 30,
) -> str:
    filtered = create_filtered_router(parent_router, allowed_tools)
    loop = AgentLoop(
        adapter=adapter,
        model=model,
        router=filtered,
        ctx=ctx,
        max_steps=max_steps,
        system_prompt=system_prompt,
    )
    final_text = ""
    async for event in loop.run(prompt):
        if event.type == "done":
            for block in event.data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    final_text += block.get("text", "")
        elif event.type == "error":
            return f"[子代理错误] {event.data.get('error', '')}"
        elif event.type == "max_steps":
            final_text += "\n[子代理达到最大步数限制]"
    return final_text or "(子代理未产生输出)"


def create_run_subagent_spec(
    adapter: ILLMAdapter,
    model: str,
    router: ToolRouter,
    ctx: ToolUseContext,
) -> ToolSpec:
    async def handler(args: dict, _ctx: ToolUseContext) -> ToolResult:
        result = await run_subagent(
            prompt=args["prompt"],
            parent_router=router,
            adapter=adapter,
            model=model,
            ctx=ctx,
            allowed_tools=args.get("allowed_tools"),
        )
        return ToolResult(content=result)

    return ToolSpec(
        name="run_subagent",
        description="在隔离上下文中派生子代理执行任务，仅返回摘要。",
        parameters=ToolParameterSchema(
            properties={
                "prompt": {"type": "string", "description": "子代理要执行的任务"},
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "允许的工具名称列表，省略则继承全部（排除递归工具）",
                },
            },
            required=["prompt"],
        ),
        handler=handler,
        timeout_ms=120_000,
    )
