"""MCP 传输层抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class McpTransport(ABC):
    """MCP 传输抽象基类。

    子类实现具体的传输方式（stdio / HTTP）。
    上层 McpClient 只调用这四个方法，不关心底层载体。
    """

    @abstractmethod
    async def connect(self) -> None:
        """建立传输连接。"""

    @abstractmethod
    async def close(self) -> None:
        """断开连接并释放资源。"""

    @abstractmethod
    async def send(self, payload: dict) -> dict:
        """发送 JSON-RPC 请求并等待响应。"""

    @abstractmethod
    async def send_notification(self, payload: dict) -> None:
        """发送 JSON-RPC 通知（无 id，不等响应）。"""
