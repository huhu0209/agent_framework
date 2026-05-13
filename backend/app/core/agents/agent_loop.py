"""最小 ReAct Agent Loop，验证 LLM Adapter 的 tool calling 链路。

ReAct = Reason + Act，每一步模型可以：
- 直接回答（stop_reason=end_turn）→ 结束
- 调用工具（stop_reason=tool_use）→ 执行工具，把结果追加到对话，继续循环
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator

from app.core.llm import (
    AssistantMessage,
    CompletionConfig,
    CompletionResult,
    ILLMAdapter,
    Message,
    StopReason,
    SystemMessage,
    TextBlock,
    ToolDefinition,
    ToolMessage,
    ToolParameterSchema,
    ToolUseBlock,
    UserMessage,
)


@dataclass
class LoopEvent:
    """Agent Loop 每一步产生的事件。"""
    type: str  # "step" | "tool_result" | "done" | "max_steps" | "error"
    step: int
    data: dict[str, Any] = field(default_factory=dict)


MOCK_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_time",
        description="获取当前日期和时间",
        parameters=ToolParameterSchema(),
    ),
    ToolDefinition(
        name="calculate",
        description="计算数学表达式",
        parameters=ToolParameterSchema(
            properties={
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式，例如 '2 + 3 * 4'",
                }
            },
            required=["expression"],
        ),
    ),
]


_SAFE_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_SAFE_UNARY_OPS = {ast.USub: operator.neg}


def _safe_eval(expr: str) -> str:
    """安全的数学表达式求值，只支持数字和基本运算符。"""
    tree = ast.parse(expr, mode="eval")

    def _eval(node: ast.expr) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            op = _SAFE_BIN_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            return op(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op = _SAFE_UNARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            return op(_eval(node.operand))
        raise ValueError(f"不支持的表达式: {ast.dump(node)}")

    return str(_eval(tree.body))


def execute_mock_tool(name: str, args: dict[str, Any]) -> str:
    """执行 mock tool，返回结果字符串。"""
    if name == "get_time":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if name == "calculate":
        return _safe_eval(args.get("expression", ""))
    return f"未知工具: {name}"


def _serialize_content(result: CompletionResult) -> list[dict[str, Any]]:
    return [b.model_dump() for b in result.content]


class AgentLoop:
    """最小 ReAct 循环，驱动 LLM 多轮 tool calling。"""

    def __init__(
        self,
        adapter: ILLMAdapter,
        *,
        model: str,
        max_steps: int = 10,
        system_prompt: str = "你是一个有用的助手。可以使用工具来完成任务。",
        tools: list[ToolDefinition] | None = None,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.max_steps = max_steps
        self.system_prompt = system_prompt
        self.tools = tools if tools is not None else MOCK_TOOLS

    def _build_config(self, messages: list[Message]) -> CompletionConfig:
        return CompletionConfig(model=self.model, messages=messages, tools=self.tools)

    def _extract_tool_calls(self, result: CompletionResult) -> list[ToolUseBlock]:
        return [b for b in result.content if isinstance(b, ToolUseBlock)]

    def _append_assistant_and_tool_results(
        self, messages: list[Message], result: CompletionResult,
    ) -> list[str]:
        """追加 AssistantMessage + 各 ToolMessage，返回每个 tool 的执行结果。"""
        messages.append(AssistantMessage(content=result.content))
        tool_results: list[str] = []
        for tc in self._extract_tool_calls(result):
            try:
                output = execute_mock_tool(tc.name, tc.input)
            except Exception as exc:
                output = f"工具执行异常: {exc}"
            messages.append(ToolMessage(tool_call_id=tc.id, content=output))
            tool_results.append(output)
        return tool_results

    async def run(self, user_message: str) -> AsyncGenerator[LoopEvent, None]:
        """核心异步生成器：执行 ReAct 循环。"""
        messages: list[Message] = [
            SystemMessage(content=self.system_prompt),
            UserMessage(content=[TextBlock(text=user_message)]),
        ]
        for step in range(1, self.max_steps + 1):
            try:
                result = await self.adapter.complete(self._build_config(messages))
            except Exception as exc:
                yield LoopEvent(type="error", step=step, data={"error": str(exc)})
                return

            yield LoopEvent(
                type="step", step=step,
                data={"stop_reason": result.stop_reason.value, "content": _serialize_content(result)},
            )

            if result.stop_reason == StopReason.END_TURN:
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
                return
            if result.stop_reason == StopReason.MAX_TOKENS:
                yield LoopEvent(type="error", step=step, data={"error": "达到 max_tokens 上限"})
                return
            if result.stop_reason == StopReason.STOP_SEQUENCE:
                yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
                return
            if result.stop_reason == StopReason.TOOL_USE:
                tool_calls = self._extract_tool_calls(result)
                if not tool_calls:
                    yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
                    return
                tool_results = self._append_assistant_and_tool_results(messages, result)
                yield LoopEvent(
                    type="tool_result", step=step,
                    data={
                        "tool_calls": [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in tool_calls],
                        "tool_results": tool_results,
                    },
                )
                continue

            # 未知 stop_reason，视为完成
            yield LoopEvent(type="done", step=step, data={"content": _serialize_content(result)})
            return

        yield LoopEvent(type="max_steps", step=self.max_steps, data={})
