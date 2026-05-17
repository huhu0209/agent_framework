"""工具执行层 — 超时、错误包装、大结果截断、参数校验。"""

from __future__ import annotations

import asyncio

from app.core.tools.types import ToolResult, ToolSpec, ToolUseContext
from app.core.tools.validator import ToolValidator


class ToolExecutor:
    """handler 外围的安全防护。"""

    MAX_RESULT_CHARS = 20_000

    def __init__(self, validator: ToolValidator | None = None) -> None:
        self._validator = validator or ToolValidator()

    async def execute(
        self, spec: ToolSpec, args: dict, ctx: ToolUseContext,
    ) -> ToolResult:
        validation_error = self._validator.validate(spec, args)
        if validation_error is not None:
            return validation_error

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

        return self._truncate_if_needed(result)

    def _truncate_if_needed(self, result: ToolResult) -> ToolResult:
        if len(result.content) <= self.MAX_RESULT_CHARS:
            return result
        truncated = result.content[: self.MAX_RESULT_CHARS]
        original_length = len(result.content)
        return ToolResult(
            content=(
                f"{truncated}\n\n"
                f"... (结果过长已截断，完整内容共 {original_length} 字符) ..."
            ),
            is_error=result.is_error,
            metadata={**result.metadata, "truncated": True, "original_length": original_length},
        )
