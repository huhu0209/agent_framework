"""内建工具集成测试。"""

import pytest
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.types import ToolUseContext


@pytest.fixture
def registry():
    return create_builtin_registry()


@pytest.fixture
def ctx(tmp_path):
    return ToolUseContext(working_dir=str(tmp_path))


class TestBuiltinRegistry:
    def test_has_three_tools(self, registry):
        assert set(registry.list_tools()) == {"read_file", "write_file", "web_search", "update_plan_status"}

    def test_definitions_valid(self, registry):
        defs = registry.get_definitions()
        assert len(defs) == 4
        for d in defs:
            assert d.name
            assert d.description


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, registry, ctx, tmp_path):
        (tmp_path / "hello.txt").write_text("hello world")

        spec = registry.get("read_file")
        result = await spec.handler({"path": "hello.txt"}, ctx)
        assert result.content == "hello world"
        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, registry, ctx):
        spec = registry.get("read_file")
        result = await spec.handler({"path": "nope.txt"}, ctx)
        assert result.is_error is True
        assert "不存在" in result.content


class TestWriteFile:
    @pytest.mark.asyncio
    async def test_write_new_file(self, registry, ctx, tmp_path):
        spec = registry.get("write_file")
        result = await spec.handler(
            {"path": "output.txt", "content": "test content"},
            ctx,
        )
        assert result.is_error is False
        assert (tmp_path / "output.txt").read_text() == "test content"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, registry, ctx, tmp_path):
        spec = registry.get("write_file")
        result = await spec.handler(
            {"path": "sub/dir/file.txt", "content": "nested"},
            ctx,
        )
        assert result.is_error is False
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text() == "nested"


class TestWebSearch:
    @pytest.mark.asyncio
    async def test_mock_search(self, registry, ctx):
        spec = registry.get("web_search")
        result = await spec.handler({"query": "test query"}, ctx)
        assert result.is_error is False
        assert "test query" in result.content
