"""搜索工具 — Tavily AsyncTavilyClient 实现。"""

from __future__ import annotations

import asyncio
import os

from tavily import AsyncTavilyClient

from agent_framework.tools.types import ToolResult, ToolUseContext


class SearchClient:
    """封装 Tavily 搜索客户端，消除模块级可变全局状态。"""

    def __init__(self, max_concurrent: int = 5) -> None:
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)
        self._client: AsyncTavilyClient | None = None

    def _get_client(self) -> AsyncTavilyClient:
        """懒加载初始化 Tavily 客户端。缺失 API key 时抛出 ValueError。"""
        if self._client is None:
            api_key = os.environ.get("TAVILY_API_KEY", "")
            if not api_key:
                raise ValueError("TAVILY_API_KEY 未配置")
            self._client = AsyncTavilyClient(api_key=api_key)
        return self._client

    async def search(self, args: dict, ctx: ToolUseContext) -> ToolResult:
        """使用 Tavily API 执行网页搜索。"""
        query = args["query"]

        try:
            async with self._semaphore:
                client = self._get_client()
                response = await client.search(query=query, max_results=5)

            results = response.get("results", [])
            if not results:
                return ToolResult(content=f"搜索 '{query}' 未找到结果。")

            lines: list[str] = []
            for i, item in enumerate(results, 1):
                title = item.get("title", "无标题")
                url = item.get("url", "")
                content = item.get("content", "")
                lines.append(f"{i}. {title}\n   {url}\n   {content}")

            return ToolResult(content="\n\n".join(lines))

        except ValueError as e:
            return ToolResult(is_error=True, content=f"搜索失败：{e}")
        except Exception as e:
            return ToolResult(is_error=True, content=f"搜索失败：{e}")

    def reset(self) -> None:
        """重置客户端实例（供测试使用）。"""
        self._client = None


# 模块级默认实例 — 向后兼容
_default_client = SearchClient()
web_search = _default_client.search
reset_client = _default_client.reset
