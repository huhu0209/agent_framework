"""PlanAndSolveAgent — 先规划后执行的 Agent 类型。"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.sub_agent import create_filtered_router
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import CompletionConfig, SystemMessage, TextBlock, UserMessage
from agent_framework.orchestrator.planner import PlanItem, parse_plan_response
from agent_framework.orchestrator.planning_session import PlanningSession
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)

_PLAN_SYSTEM_PROMPT = (
    "你是一个任务规划专家。将用户任务分解为有序步骤。\n"
    "在 <plan>...</plan> 标签中输出计划，每步一行，格式：\n"
    "1. 步骤描述\n"
    "2. 步骤描述\n"
    "...\n"
    "只输出计划，不要解释。"
)


class PlanAndSolveAgent(Agent):
    """先规划后执行的 Agent：调用 LLM 生成计划，逐步执行，偏离时重新规划。"""

    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        max_steps_per_plan_item: int = 10,
        max_replans: int = 2,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self.max_steps_per_plan_item = max_steps_per_plan_item
        self.max_replans = max_replans
        self._planning = PlanningSession(
            allow_replan=False,
            drift_warn=3,
            drift_abort=max_replans,
        )

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """执行 Plan-and-Solve 流程。"""
        # Step 1: generate plan
        plan_items = await self._generate_plan(user_message)

        # Step 2: empty plan fallback
        if not plan_items:
            yield AgentEvent(
                type="step", step=0,
                data={"text": "无法生成计划，回退到直接执行"},
            )
            async for event in self._run_fallback(user_message):
                yield event
            return

        # Step 3: execute plan step by step
        self._planning.create_from_items(plan_items, "llm_generated")
        replan_count = 0
        step_outputs: list[str] = []
        global_step = 0
        i = 0

        while i < len(plan_items):
            item = plan_items[i]
            self._planning.update_status(item.id, "in_progress")
            step_prompt = self._build_step_prompt(user_message, item, step_outputs)

            # Execute step with independent AgentLoop
            filtered_router = create_filtered_router(self.router, None)
            loop = AgentLoop(
                adapter=self.adapter,
                model=self.model,
                router=filtered_router,
                ctx=self.ctx,
                max_steps=self.max_steps_per_plan_item,
            )
            result_text = await self._collect_loop_output(loop, step_prompt)

            global_step += 1
            yield AgentEvent(
                type="step", step=global_step,
                data={"text": f"[{item.id}] {item.action}\n{result_text}"},
            )

            step_outputs.append(result_text)
            self._planning.update_status(item.id, "completed")

            # Step 4: step failure detection (replaces drift detection)
            if self._is_step_failed(result_text):
                replan_count += 1
                if replan_count <= self.max_replans:
                    yield AgentEvent(
                        type="step", step=global_step,
                        data={"text": f"检测到偏离，重新规划 (第{replan_count}次)"},
                    )
                    new_plan = await self._generate_plan(user_message)
                    if new_plan:
                        plan_items = new_plan
                        self._planning.create_from_items(plan_items, "llm_generated")
                        step_outputs = []
                        i = 0
                        continue
                    # New plan generation failed, continue with current plan
                else:
                    yield AgentEvent(
                        type="error", step=global_step,
                        data={"error_message": f"偏离次数达到上限 {self.max_replans} 次"},
                    )
                    return

            i += 1

        # Step 5: done
        final_summary = "\n".join(step_outputs)
        yield AgentEvent(
            type="done", step=global_step,
            data={"text": final_summary[-2000:] if len(final_summary) > 2000 else final_summary},
        )

    async def _generate_plan(self, user_message: str) -> list[PlanItem] | None:
        """调用 LLM 生成计划。"""
        response_text = await self._call_llm(_PLAN_SYSTEM_PROMPT, user_message)
        return parse_plan_response(response_text)

    def _build_step_prompt(
        self, user_message: str, item: PlanItem, step_outputs: list[str],
    ) -> str:
        """构造步骤执行 prompt：原始任务 + 当前步骤 + 前序摘要。"""
        parts = [f"原始任务：{user_message}", "", f"当前步骤：{item.action}"]
        if step_outputs:
            summary = "\n".join(step_outputs)
            if len(summary) > 2000:
                summary = summary[-2000:]
            parts.append("")
            parts.append(f"前序步骤摘要：\n{summary}")
        return "\n".join(parts)

    def _is_step_failed(self, result: str) -> bool:
        """规则检查：判断单步执行结果是否异常（空输出、子代理错误）。"""
        if not result or not result.strip():
            return True
        if "[子代理错误]" in result:
            return True
        return False

    async def _collect_loop_output(self, loop: AgentLoop, prompt: str) -> str:
        """从 AgentLoop 收集最终输出文本。"""
        final_text = ""
        async for event in loop.run(prompt):
            if event.type == "done":
                content = event.data.get("content", [])
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        final_text += block.get("text", "")
            elif event.type == "error":
                return f"[子代理错误] {event.data.get('error', '')}"
            elif event.type == "max_steps":
                final_text += "\n[达到最大步数限制]"
        return final_text or "(未产生输出)"

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """构造 CompletionConfig 并调用 LLM，返回文本响应。"""
        config = CompletionConfig(
            model=self.model,
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=[TextBlock(text=user_prompt)]),
            ],
        )
        result = await self.adapter.complete(config)
        for block in result.content:
            if isinstance(block, TextBlock):
                return block.text
        return ""

    async def _run_fallback(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """空计划 fallback：直接使用 AgentLoop ReAct 执行。"""
        filtered_router = create_filtered_router(self.router, None)
        loop = AgentLoop(
            adapter=self.adapter,
            model=self.model,
            router=filtered_router,
            ctx=self.ctx,
            max_steps=self.max_steps_per_plan_item,
        )
        async for event in loop.run(user_message):
            yield event
