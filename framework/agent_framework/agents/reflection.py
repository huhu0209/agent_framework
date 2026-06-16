"""ReflectionAgent — 执行→反省→改进循环的 Agent 类型。"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import AsyncGenerator

from agent_framework.agents.base import Agent, AgentEvent
from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.agents.event_utils import extract_text_from_content
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionConfig,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext

logger = logging.getLogger(__name__)

# ============================================================
# ReflectionVerdict
# ============================================================


@dataclass
class ReflectionVerdict:
    """LLM 评估输出的结构化判定结果。"""

    satisfied: bool
    scores: dict[str, int] = field(default_factory=dict)
    critique: str = ""

    @classmethod
    def from_llm_response(cls, text: str) -> ReflectionVerdict:
        """从 LLM 响应文本解析 verdict，容错处理。"""
        # Find the last outermost brace pair to handle nested JSON
        # (e.g., scores: {"correctness": 3})
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match is None:
            return cls(
                satisfied=False,
                scores={},
                critique=f"评估失败，原始输出：{text[:200]}",
            )
        try:
            data = json.loads(match.group())
            return cls(
                satisfied=bool(data.get("satisfied", False)),
                scores=data.get("scores", {}),
                critique=data.get("critique", ""),
            )
        except (json.JSONDecodeError, ValueError, AttributeError):
            return cls(
                satisfied=False,
                scores={},
                critique=f"评估失败，原始输出：{text[:200]}",
            )


# ============================================================
# ReflectionAgent
# ============================================================

_REFLECT_SYSTEM_PROMPT = "你是一个输出质量评估专家。请严格按照 JSON 格式回复。"

_REFLECT_USER_TEMPLATE = (
    "请评估以下任务执行的输出质量。\n\n"
    "## 原始任务\n{task}\n\n"
    "## 执行输出\n{output}\n\n"
    "## 评估要求\n"
    "从三个维度评分（各 1-5 分）：\n"
    "1. 正确性：输出是否正确回答了任务\n"
    "2. 完整性：输出是否有遗漏\n"
    "3. 清晰度：输出是否清晰明了\n\n"
    "请严格按照以下 JSON 格式回复，不要包含其他内容：\n"
    '{{"satisfied": true/false, "scores": {{"correctness": N, "completeness": N, "clarity": N}}, "critique": "具体改进建议"}}'
)


class ReflectionAgent(Agent):
    """执行→反省→改进循环的 Agent。

    执行和改进阶段复用 AgentLoop（保留工具调用能力），
    评估阶段用独立 LLM completion（不做 tool calling）。
    改进轮次硬上限由 max_improvement_rounds 控制（默认 2）。
    """

    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        router: ToolRouter,
        ctx: ToolUseContext,
        max_improvement_rounds: int = 2,
        max_steps_per_round: int = 10,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.router = router
        self.ctx = ctx
        self.max_improvement_rounds = max_improvement_rounds
        self.max_steps_per_round = max_steps_per_round

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """执行→反省→改进循环。"""
        current_prompt = user_message
        global_step = 0
        output = ""
        verdict: ReflectionVerdict | None = None

        for round_num in range(self.max_improvement_rounds + 1):
            # a. 执行阶段 — 创建新的 AgentLoop 实例
            output, steps = await self._collect_loop_output(current_prompt)
            global_step += steps

            # b. 评估阶段 — 独立 LLM completion
            verdict = await self._reflect(user_message, output)

            # c. 满意判定
            if verdict.satisfied:
                yield AgentEvent(
                    type="done",
                    step=global_step,
                    data={
                        "text": output,
                        "verdict": {
                            "satisfied": True,
                            "scores": verdict.scores,
                        },
                    },
                )
                return

            # d. 改进准备
            if round_num < self.max_improvement_rounds:
                yield AgentEvent(
                    type="step",
                    step=global_step,
                    data={
                        "text": f"评估不满意，开始第{round_num + 1}次改进",
                        "verdict": {
                            "satisfied": False,
                            "scores": verdict.scores,
                            "critique": verdict.critique,
                        },
                    },
                )
                current_prompt = (
                    f"{user_message}\n\n"
                    f"[评估反馈]\n{verdict.critique}\n\n"
                    f"请根据以上反馈改进。"
                )

        # 循环结束 — 达到改进上限
        yield AgentEvent(
            type="done",
            step=global_step,
            data={
                "text": output,
                "verdict": {
                    "satisfied": False,
                    "scores": verdict.scores if verdict else {},
                    "critique": verdict.critique if verdict else "",
                    "max_rounds_reached": True,
                },
            },
        )

    async def _collect_loop_output(self, prompt: str) -> tuple[str, int]:
        """执行 AgentLoop 并收集最终输出文本和步数。"""
        loop = AgentLoop(
            self.adapter,
            model=self.model,
            router=self.router,
            ctx=self.ctx,
            max_steps=self.max_steps_per_round,
        )
        output_text = ""
        step_count = 0
        async for event in loop.run(prompt):
            step_count += 1
            if event.type == "done":
                content = event.data.get("content", [])
                output_text = extract_text_from_content(content, first_only=True)
                if not output_text and content:
                    first = content[0]
                    if isinstance(first, dict):
                        output_text = first.get("text", "")
        return output_text, step_count

    async def _reflect(
        self, user_message: str, output: str
    ) -> ReflectionVerdict:
        """评估输出质量，返回 ReflectionVerdict。"""
        user_prompt = _REFLECT_USER_TEMPLATE.format(
            task=user_message, output=output
        )
        response_text = await self._call_llm(_REFLECT_SYSTEM_PROMPT, user_prompt)
        return ReflectionVerdict.from_llm_response(response_text)

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """独立 LLM completion（不传 tools，纯文本）。"""
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
