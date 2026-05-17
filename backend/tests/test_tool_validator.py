"""ToolValidator 参数校验测试。"""

import pytest
from app.core.tools.validator import ToolValidator
from app.core.tools.types import ToolResult, ToolSpec
from app.core.llm.types import ToolParameterSchema


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

    def test_extra_args_pass(self):
        """额外的参数不报错（forward compatible）。"""
        spec = _make_spec(
            properties={"path": {"type": "string"}},
            required=["path"],
        )
        assert validator.validate(spec, {"path": "/tmp/a.txt", "extra": 123}) is None

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
