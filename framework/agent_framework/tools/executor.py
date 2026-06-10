"""工具执行层 — 超时、错误包装、大结果截断、参数校验。"""

from __future__ import annotations

import asyncio

from agent_framework.tools.context.result_truncator import truncate_if_needed
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext
from agent_framework.tools.validator import ToolValidator


class ToolExecutor:
    """handler 外围的安全防护。"""

    def __init__(self, validator: ToolValidator | None = None) -> None:
        self._validator = validator or ToolValidator()

    async def execute(
        self, spec: ToolSpec, args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        validation_error = self._validator.validate(spec, args)
        if validation_error is not None:
            return validation_error

        if spec.handler is None:
            return ToolResult(
                content=f"工具 '{spec.name}' 不可执行（无 handler）。",
                is_error=True,
            )

        try:
            result = await asyncio.wait_for(
                spec.handler(args, ctx),
                timeout=spec.timeout_ms / 1000,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                content=(
                    f"工具 '{spec.name}' 执行超时 ({spec.timeout_ms}ms)。"
                    f"建议：检查参数或缩短查询范围。"
                ),
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=(
                    f"工具 '{spec.name}' 执行失败: {e}。"
                    f"建议：检查参数是否正确。"
                ),
                is_error=True,
            )

        return await truncate_if_needed(result, spec.name, ctx.working_dir)
