"""ToolValidator 参数校验测试。"""

import pytest
from agent_framework.tools.validator import ToolValidator
from agent_framework.tools.types import ToolResult, ToolSpec
from agent_framework.llm.types import ToolParameterSchema


def _make_spec(name: str = "test", properties=None, required=None) -> ToolSpec:
    return ToolSpec(
        name=name,
        description="test",
        parameters=ToolParameterSchema(
            properties=properties or {},
            required=required or [],
        ),
        handler=lambda args, ctx: None,
    )


validator = ToolValidator()


class TestToolValidator:
    def test_no_params_pass(self):
        spec = _make_spec()
        assert validator.validate(spec, {}) is None

    def test_required_present_pass(self):
        spec = _make_spec(
            properties={"path": {"type": "string"}},
            required=["path"],
        )
        assert validator.validate(spec, {"path": "/tmp/a.txt"}) is None

    def test_required_missing_returns_error(self):
        spec = _make_spec(
            properties={"path": {"type": "string"}},
            required=["path"],
        )
        result = validator.validate(spec, {})
        assert isinstance(result, ToolResult)
        assert result.is_error is True
        assert "path" in result.content

    def test_wrong_type_returns_error(self):
        spec = _make_spec(
            properties={"count": {"type": "integer"}},
            required=["count"],
        )
        result = validator.validate(spec, {"count": "not_a_number"})
        assert isinstance(result, ToolResult)
        assert result.is_error is True

    def test_extra_args_rejected(self):
        """额外的未知参数报错（strict validation）。"""
        spec = _make_spec(
            properties={"path": {"type": "string"}},
            required=["path"],
        )
        result = validator.validate(spec, {"path": "/tmp/a.txt", "extra": 123})
        assert isinstance(result, ToolResult)
        assert result.is_error is True

    def test_optional_param_missing_pass(self):
        """非必填参数缺失不报错。"""
        spec = _make_spec(
            properties={"path": {"type": "string"}, "encoding": {"type": "string"}},
            required=["path"],
        )
        assert validator.validate(spec, {"path": "/tmp/a.txt"}) is None

    def test_type_check_string(self):
        spec = _make_spec(properties={"name": {"type": "string"}}, required=["name"])
        assert validator.validate(spec, {"name": 123}) is not None
        assert validator.validate(spec, {"name": "hello"}) is None

    def test_type_check_integer(self):
        spec = _make_spec(properties={"n": {"type": "integer"}}, required=["n"])
        assert validator.validate(spec, {"n": "abc"}) is not None
        assert validator.validate(spec, {"n": 42}) is None
        assert validator.validate(spec, {"n": True}) is not None

    def test_type_check_number(self):
        spec = _make_spec(properties={"n": {"type": "number"}}, required=["n"])
        assert validator.validate(spec, {"n": "abc"}) is not None
        assert validator.validate(spec, {"n": 3.14}) is None
        assert validator.validate(spec, {"n": 42}) is None

    def test_enum_rejects_invalid_value(self):
        """参数值不在 enum 列表中时返回错误。"""
        spec = _make_spec(
            properties={"event_type": {"type": "string", "enum": ["decision", "preference"]}},
            required=["event_type"],
        )
        result = validator.validate(spec, {"event_type": "invalid"})
        assert isinstance(result, ToolResult)
        assert result.is_error is True
        assert "enum" in result.content

    def test_enum_passes_valid_value(self):
        """参数值在 enum 列表中时通过。"""
        spec = _make_spec(
            properties={"event_type": {"type": "string", "enum": ["decision", "preference"]}},
            required=["event_type"],
        )
        assert validator.validate(spec, {"event_type": "decision"}) is None

    def test_enum_passes_when_no_enum_defined(self):
        """schema 中没有 enum 时不做枚举校验。"""
        spec = _make_spec(
            properties={"name": {"type": "string"}},
            required=["name"],
        )
        assert validator.validate(spec, {"name": "anything"}) is None

    def test_unknown_parameter_rejected(self):
        """参数名不在 schema.properties 中时返回错误。"""
        spec = _make_spec(
            properties={"path": {"type": "string"}},
            required=["path"],
        )
        result = validator.validate(spec, {"path": "/tmp/a", "unknown_field": 42})
        assert isinstance(result, ToolResult)
        assert result.is_error is True
        assert "unknown" in result.content

    def test_known_parameter_not_unknown(self):
        """参数名在 schema.properties 中时不被标记为 unknown。"""
        spec = _make_spec(
            properties={"path": {"type": "string"}},
            required=["path"],
        )
        assert validator.validate(spec, {"path": "/tmp/a"}) is None
