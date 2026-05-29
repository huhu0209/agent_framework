"""搜索工具 — Tavily AsyncTavilyClient 实现。"""

from __future__ import annotations

import asyncio
import os

from tavily import AsyncTavilyClient

from agent_framework.tools.types import ToolResult, ToolUseContext

# 模块级并发控制（SRCH-02）
_semaphore: asyncio.Semaphore = asyncio.Semaphore(5)

# 懒加载单例客户端
_client: AsyncTavilyClient | None = None


def _get_client() -> AsyncTavilyClient:
    """懒加载初始化 Tavily 客户端。缺失 API key 时抛出 ValueError。"""
    global _client
    if _client is None:
        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            raise ValueError("TAVILY_API_KEY 未配置")
        _client = AsyncTavilyClient(api_key=api_key)
    return _client


def reset_client() -> None:
    """重置客户端单例（供测试使用）。"""
    global _client
    _client = None


async def web_search(args: dict, ctx: ToolUseContext) -> ToolResult:
    """使用 Tavily API 执行网页搜索。"""
    query = args["query"]

    try:
        async with _semaphore:
            client = _get_client()
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
