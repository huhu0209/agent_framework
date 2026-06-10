"""MCP 传输层抽象。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

_ALLOWED_ENV_KEYS: frozenset[str] = frozenset({
    "PATH", "HOME", "TEMP", "TMP", "TMPDIR", "USER", "LANG", "SYSTEMROOT",
})


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


class StdioTransport(McpTransport):
    """stdio 传输 — 通过子进程 stdin/stdout 通信，Content-Length 分帧。"""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._command = command
        self._args = args or []
        self._env = env
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._pending_future: asyncio.Future | None = None
        self._notification_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None

    async def connect(self) -> None:
        base_env = {k: v for k, v in os.environ.items() if k in _ALLOWED_ENV_KEYS}
        env = {**base_env, **(self._env or {})}
        self._process = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._reader_task = asyncio.create_task(self._read_loop())

    async def send(self, payload: dict) -> dict:
        async with self._lock:
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self._pending_future = future
            await self._write(payload)
            return await future

    async def send_notification(self, payload: dict) -> None:
        await self._write(payload)

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._process and self._process.returncode is None:
            if self._pending_future and not self._pending_future.done():
                self._pending_future.set_exception(
                    ConnectionError("MCP server 已关闭")
                )
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
            await self._process.communicate()

    async def _write(self, payload: dict) -> None:
        body = json.dumps(payload)
        frame = f"Content-Length: {len(body)}\r\n\r\n{body}"
        self._process.stdin.write(frame.encode())
        await self._process.stdin.drain()

    async def _read_loop(self) -> None:
        try:
            while True:
                header = await self._read_until_header_end()
                length = self._parse_content_length(header)
                body = await self._read_exact(length)
                msg = json.loads(body)
                if "id" in msg:
                    if self._pending_future and not self._pending_future.done():
                        self._pending_future.set_result(msg)
                else:
                    self._notification_queue.put_nowait(msg)
        except (EOFError, asyncio.IncompleteReadError):
            if self._pending_future and not self._pending_future.done():
                self._pending_future.set_exception(
                    ConnectionError("MCP server 已退出")
                )

    async def _read_until_header_end(self) -> bytes:
        buf = b""
        while True:
            line = await self._process.stdout.readline()
            if not line:
                raise EOFError("MCP server 关闭了连接")
            buf += line
            if buf.endswith(b"\r\n\r\n"):
                return buf

    @staticmethod
    def _parse_content_length(header: bytes) -> int:
        for line in header.decode().split("\r\n"):
            if line.lower().startswith("content-length:"):
                return int(line.split(":")[1].strip())
        raise ValueError("MCP 消息缺少 Content-Length header")

    async def _read_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = await self._process.stdout.read(n - len(buf))
            if not chunk:
                raise EOFError("MCP server 关闭了连接")
            buf += chunk
        return buf
