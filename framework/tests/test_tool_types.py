"""Tool System 数据模型测试。"""

import pytest
from agent_framework.tools.types import ToolCall, ToolResult, ToolSpec, ToolUseContext
from agent_framework.llm.types import ToolDefinition, ToolParameterSchema


class TestToolCall:
    def test_create(self):
        tc = ToolCall(id="tc_1", name="read_file", arguments={"path": "/tmp/a.txt"})
        assert tc.id == "tc_1"
        assert tc.name == "read_file"
        assert tc.arguments == {"path": "/tmp/a.txt"}

    def test_default_arguments(self):
        tc = ToolCall(id="tc_2", name="get_time", arguments={})
        assert tc.arguments == {}


class TestToolResult:
    def test_success_result(self):
        r = ToolResult(content="file content here")
        assert r.content == "file content here"
        assert r.is_error is False
        assert r.metadata == {}

    def test_error_result(self):
        r = ToolResult(content="文件不存在", is_error=True)
        assert r.is_error is True

    def test_with_metadata(self):
        r = ToolResult(content="ok", metadata={"duration_ms": 150})
        assert r.metadata["duration_ms"] == 150


class TestToolSpec:
    def test_create_and_to_definition(self):
        async def fake_handler(args, ctx):
            return ToolResult(content="ok")

        spec = ToolSpec(
            name="read_file",
            description="读取文件内容",
            parameters=ToolParameterSchema(
                properties={"path": {"type": "string", "description": "文件路径"}},
                required=["path"],
            ),
            handler=fake_handler,
            timeout_ms=10_000,
        )
        assert spec.name == "read_file"
        assert spec.timeout_ms == 10_000

        defn = spec.to_tool_definition()
        assert isinstance(defn, ToolDefinition)
        assert defn.name == "read_file"
        assert defn.description == "读取文件内容"
        assert "path" in defn.parameters.properties

    def test_handler_not_in_definition(self):
        """handler 不应该出现在 ToolDefinition 序列化中。"""
        async def fake_handler(args, ctx):
            return ToolResult(content="ok")

        spec = ToolSpec(
            name="test",
            description="test",
            parameters=ToolParameterSchema(),
            handler=fake_handler,
        )
        defn = spec.to_tool_definition()
        dumped = defn.model_dump()
        assert "handler" not in dumped

    def test_default_timeout(self):
        async def fake_handler(args, ctx):
            return ToolResult(content="ok")

        spec = ToolSpec(
            name="test", description="test",
            parameters=ToolParameterSchema(), handler=fake_handler,
        )
        assert spec.timeout_ms == 30_000


class TestToolUseContext:
    def test_defaults(self):
        ctx = ToolUseContext()
        assert ctx.working_dir == "."
        assert ctx.message_history == []
        assert ctx.mcp_clients == {}

    def test_custom_working_dir(self):
        ctx = ToolUseContext(working_dir="/tmp/project")
        assert ctx.working_dir == "/tmp/project"
