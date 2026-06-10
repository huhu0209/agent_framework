"""search_tools 测试 — Mock AsyncTavilyClient，不依赖真实 API。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agent_framework.tools.builtin.search_tools import SearchClient, web_search
from agent_framework.tools.types import ToolUseContext


@pytest.fixture
def ctx(tmp_path):
    return ToolUseContext(working_dir=str(tmp_path))


@pytest.fixture
def client():
    """每个测试创建独立的 SearchClient 实例。"""
    return SearchClient()


@pytest.fixture(autouse=True)
def _reset_default_client():
    """每个测试前重置模块级默认客户端。"""
    from agent_framework.tools.builtin.search_tools import reset_client

    reset_client()
    yield
    reset_client()


class TestSearchSuccess:
    @pytest.mark.asyncio
    async def test_search_returns_results_on_success(self, ctx, client):
        mock_tavily = AsyncMock()
        mock_tavily.search.return_value = {
            "results": [
                {
                    "title": "Python Tutorial",
                    "url": "https://example.com/python",
                    "content": "Learn Python programming",
                }
            ]
        }

        with patch.object(client, "_get_client", return_value=mock_tavily):
            result = await client.search({"query": "Python tutorial"}, ctx)

        assert result.is_error is False
        assert "Python Tutorial" in result.content
        assert "https://example.com/python" in result.content
        assert "Learn Python programming" in result.content


class TestSearchErrors:
    @pytest.mark.asyncio
    async def test_search_returns_error_on_missing_api_key(self, ctx, client, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        client.reset()

        result = await client.search({"query": "test"}, ctx)
        assert result.is_error is True
        assert "搜索失败" in result.content
        assert "TAVILY_API_KEY 未配置" in result.content

    @pytest.mark.asyncio
    async def test_search_returns_error_on_network_failure(self, ctx, client):
        mock_tavily = AsyncMock()
        mock_tavily.search.side_effect = ConnectionError("timeout")

        with patch.object(client, "_get_client", return_value=mock_tavily):
            result = await client.search({"query": "test"}, ctx)

        assert result.is_error is True
        assert "搜索失败" in result.content
        assert "timeout" in result.content


class TestSearchSemaphore:
    def test_semaphore_limits_concurrency(self, client):
        assert client._semaphore._value == 5

    @pytest.mark.asyncio
    async def test_semaphore_enforces_max_5_concurrent(self, ctx, client):
        """启动 10 个并发搜索，验证同时运行的不超过 5 个。"""
        active_count = 0
        max_active = 0

        async def mock_search(**kwargs):
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.05)
            active_count -= 1
            return {"results": [{"title": "t", "url": "u", "content": "c"}]}

        mock_tavily = AsyncMock()
        mock_tavily.search = mock_search

        with patch.object(client, "_get_client", return_value=mock_tavily):
            tasks = [client.search({"query": f"q{i}"}, ctx) for i in range(10)]
            await asyncio.gather(*tasks)

        assert max_active <= 5


class TestSearchResultFormat:
    @pytest.mark.asyncio
    async def test_search_result_format(self, ctx, client):
        mock_tavily = AsyncMock()
        mock_tavily.search.return_value = {
            "results": [
                {"title": "Title A", "url": "https://a.com", "content": "Content A"},
                {"title": "Title B", "url": "https://b.com", "content": "Content B"},
                {"title": "Title C", "url": "https://c.com", "content": "Content C"},
            ]
        }

        with patch.object(client, "_get_client", return_value=mock_tavily):
            result = await client.search({"query": "test"}, ctx)

        assert result.is_error is False
        assert "1. Title A" in result.content
        assert "2. Title B" in result.content
        assert "3. Title C" in result.content
        assert "https://a.com" in result.content
        assert "https://b.com" in result.content
        assert "https://c.com" in result.content

    @pytest.mark.asyncio
    async def test_search_empty_results(self, ctx, client):
        mock_tavily = AsyncMock()
        mock_tavily.search.return_value = {"results": []}

        with patch.object(client, "_get_client", return_value=mock_tavily):
            result = await client.search({"query": "obscure query"}, ctx)

        assert result.is_error is False
        assert "未找到结果" in result.content


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_module_level_web_search_delegates_to_default_client(self, ctx):
        """模块级 web_search 仍然可用（向后兼容）。"""
        mock_tavily = AsyncMock()
        mock_tavily.search.return_value = {
            "results": [{"title": "t", "url": "u", "content": "c"}]
        }

        with patch(
            "agent_framework.tools.builtin.search_tools._default_client._get_client",
            return_value=mock_tavily,
        ):
            result = await web_search({"query": "test"}, ctx)

        assert result.is_error is False
        assert "t" in result.content

    def test_module_level_reset_client_delegates_to_default_client(self):
        """模块级 reset_client 仍然可用（向后兼容）。"""
        from agent_framework.tools.builtin.search_tools import (
            _default_client,
            reset_client,
        )

        reset_client()
        assert _default_client._client is None
