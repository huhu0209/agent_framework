"""工具参数校验。只使用 JSON Schema 最大公约子集。"""

from __future__ import annotations

from agent_framework.tools.types import ToolResult, ToolSpec


_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


class ToolValidator:
    """基于 JSON Schema 最大公约子集的参数校验。"""

    def validate(self, spec: ToolSpec, args: dict) -> ToolResult | None:
        """None = 通过, ToolResult = 校验失败。"""
        schema = spec.parameters

        # 1. 检查 required 字段
        for field_name in schema.required:
            if field_name not in args:
                return ToolResult(
                    content=f"参数校验失败: 缺少必填参数 '{field_name}'",
                    is_error=True,
                )

        # 2. 检查已提供参数的 type
        for field_name, value in args.items():
            prop_schema = schema.properties.get(field_name)
            if prop_schema is None:
                continue

            expected_type = prop_schema.get("type")
            if expected_type and expected_type in _TYPE_CHECKERS:
                if not _TYPE_CHECKERS[expected_type](value):
                    actual_type = type(value).__name__
                    return ToolResult(
                        content=(
                            f"参数校验失败: '{field_name}' 应为 {expected_type}，"
                            f"实际为 {actual_type}"
                        ),
                        is_error=True,
                    )

        # 3. 检查 enum 约束
        for field_name, value in args.items():
            prop_schema = schema.properties.get(field_name)
            if prop_schema is None:
                continue
            enum_list = prop_schema.get("enum")
            if enum_list is not None and value not in enum_list:
                return ToolResult(
                    content=(
                        f"Parameter validation failed: '{field_name}' value "
                        f"'{value}' not in enum {enum_list}"
                    ),
                    is_error=True,
                )

        # 4. 检查未知参数（仅对可信 schema；MCP 远程 schema 不可信，H-C2 设 strict_unknown_params=False 跳过）
        if spec.strict_unknown_params:
            for field_name in args:
                if field_name not in schema.properties:
                    return ToolResult(
                        content=(
                            f"Parameter validation failed: unknown parameter "
                            f"'{field_name}'"
                        ),
                        is_error=True,
                    )

        return None
