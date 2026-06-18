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
        assert set(registry.list_tools()) == {
            "read_file", "write_file", "web_search",
            "update_plan_status", "memory_search", "memory_write",
        }

    def test_definitions_valid(self, registry):
        defs = registry.get_definitions()
        assert len(defs) == 6
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

    @pytest.mark.asyncio
    async def test_read_file_rejects_oversized(self, registry, ctx, tmp_path, monkeypatch):
        """C4: 超过大小上限的文件被拒绝，不 OOM。"""
        from agent_framework.tools.builtin import file_tools
        monkeypatch.setattr(file_tools, "_MAX_READ_BYTES", 10)  # 小上限加速测试

        (tmp_path / "big.txt").write_text("x" * 11)
        spec = registry.get("read_file")
        result = await spec.handler({"path": "big.txt"}, ctx)
        assert result.is_error is True
        assert "过大" in result.content

    @pytest.mark.asyncio
    async def test_read_file_under_limit_still_reads(self, registry, ctx, tmp_path, monkeypatch):
        """C4: 上限内的文件正常读取（回归保护）。"""
        from agent_framework.tools.builtin import file_tools
        monkeypatch.setattr(file_tools, "_MAX_READ_BYTES", 100)

        (tmp_path / "small.txt").write_text("hello world")
        spec = registry.get("read_file")
        result = await spec.handler({"path": "small.txt"}, ctx)
        assert result.is_error is False
        assert result.content == "hello world"


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


class TestPathSandbox:
    """路径沙箱测试 — 防止路径遍历和绝对路径攻击。"""

    @pytest.mark.asyncio
    async def test_read_file_rejects_traversal(self, registry, ctx):
        spec = registry.get("read_file")
        result = await spec.handler({"path": "../../../etc/passwd"}, ctx)
        assert result.is_error is True
        assert "拒绝" in result.content

    @pytest.mark.asyncio
    async def test_read_file_rejects_absolute_path(self, registry, ctx):
        spec = registry.get("read_file")
        result = await spec.handler({"path": "/etc/shadow"}, ctx)
        assert result.is_error is True
        assert "拒绝" in result.content

    @pytest.mark.asyncio
    async def test_write_file_rejects_traversal(self, registry, ctx):
        spec = registry.get("write_file")
        result = await spec.handler(
            {"path": "../../tmp/evil.txt", "content": "hack"}, ctx,
        )
        assert result.is_error is True
        assert "拒绝" in result.content

    @pytest.mark.asyncio
    async def test_write_file_rejects_absolute_path(self, registry, ctx):
        spec = registry.get("write_file")
        result = await spec.handler(
            {"path": "/tmp/evil.txt", "content": "hack"}, ctx,
        )
        assert result.is_error is True
        assert "拒绝" in result.content

    @pytest.mark.asyncio
    async def test_error_no_path_leak(self, registry, ctx):
        spec = registry.get("read_file")
        result = await spec.handler({"path": "../../../etc/passwd"}, ctx)
        assert result.is_error is True
        # 错误消息不得泄露实际路径信息
        assert "etc" not in result.content
        assert "passwd" not in result.content
        # 也不应包含解析后的绝对路径
        assert "/" not in result.content or "拒绝" in result.content


class TestWebSearch:
    @pytest.mark.asyncio
    async def test_search_via_registry(self, registry, ctx):
        from unittest.mock import AsyncMock, patch

        mock_tavily = AsyncMock()
        mock_tavily.search.return_value = {
            "results": [
                {"title": "Test", "url": "https://example.com", "content": "test query info"}
            ]
        }

        spec = registry.get("web_search")
        # handler 是 SearchClient 实例的 bound method，直接 patch 实例
        handler_self = spec.handler.__self__
        with patch.object(handler_self, "_get_client", return_value=mock_tavily):
            result = await spec.handler({"query": "test query"}, ctx)

        assert result.is_error is False
        assert "test query" in result.content


class TestBuiltinAnnotations:
    """B3: 内置工具必须声明 annotations，供权限管道做风险决策。"""

    def test_read_file_is_readonly(self, registry):
        spec = registry.get("read_file")
        assert spec is not None
        assert spec.annotations.get("readOnly") is True

    def test_write_file_is_destructive(self, registry):
        spec = registry.get("write_file")
        assert spec is not None
        assert spec.annotations.get("destructive") is True

    def test_web_search_is_openworld(self, registry):
        spec = registry.get("web_search")
        assert spec is not None
        assert spec.annotations.get("openWorld") is True

    def test_memory_write_is_destructive(self, registry):
        spec = registry.get("memory_write")
        assert spec is not None
        assert spec.annotations.get("destructive") is True

    def test_memory_search_is_readonly(self, registry):
        spec = registry.get("memory_search")
        assert spec is not None
        assert spec.annotations.get("readOnly") is True

    def test_update_plan_status_is_destructive(self, registry):
        spec = registry.get("update_plan_status")
        assert spec is not None
        assert spec.annotations.get("destructive") is True
