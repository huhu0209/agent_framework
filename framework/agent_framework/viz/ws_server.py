"""WebSocket 服务端 — 订阅 EventBus 推送 VizEvent + 处理控制命令。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from agent_framework.viz.event_bus import EventBus

logger = logging.getLogger(__name__)

_active_runners: dict[str, asyncio.Task[None]] = {}


async def serve_ws(
    bus: EventBus,
    host: str = "localhost",
    port: int = 8765,
    *,
    token: str | None = None,
    allowed_origins: list[str] | None = None,
    production: bool = False,
    snapshot_provider: Any = None,  # Callable[[str], list[dict] | None]
) -> None:
    """启动 WebSocket 服务端。

    B4: production=True 时 token 必须提供（fail-safe，防无认证裸奔）。
    allowed_origins 非 None 时启用 Origin 白名单校验（CSWSH 防护）。
    snapshot_provider: 注入的 Callable[[session_id], list[dict] | None]，
    供 get_snapshot 命令重推会话 config/system_prompt 快照（晚连接拉回）。
    """
    if production and token is None:
        raise ValueError("production mode requires a token")

    if token is not None:
        logger.info("WebSocket server listening on ws://%s:%d (auth enabled)", host, port)
    else:
        logger.info("WebSocket server listening on ws://%s:%d (no auth, development mode)", host, port)

    async with serve(
        lambda ws: _handler(ws, bus, token, allowed_origins, snapshot_provider), host, port
    ) as server:
        await server.wait_closed()


async def _handler(
    websocket: ServerConnection,
    bus: EventBus,
    token: str | None = None,
    allowed_origins: list[str] | None = None,
    snapshot_provider: Any = None,
) -> None:
    """处理单个 WebSocket 连接：推送事件 + 接收命令。"""

    # B4: Origin 白名单校验（CSWSH 防护）——浏览器任意网页可发起 WS 连接，
    # 无 Origin 校验时恶意页面可借用户会话发 start_team/stop_team。
    if allowed_origins is not None:
        origin = websocket.request.headers.get("Origin")
        if origin not in allowed_origins:
            await websocket.close(code=4003, reason="Origin not allowed")
            return

    # Token authentication check
    if token is not None:
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(websocket.request.path).query)
        client_token = query.get("token", [None])[0]
        if client_token != token:
            await websocket.close(code=4001, reason="Unauthorized")
            return

    queue = await bus.subscribe()
    try:
        recv_task = asyncio.create_task(_handle_commands(websocket, bus, snapshot_provider))
        push_task = asyncio.create_task(_push_events(websocket, queue))
        done, pending = await asyncio.wait(
            [recv_task, push_task], return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            try:
                task.result()
            except Exception:
                logger.debug("Task cleanup error", exc_info=True)
    finally:
        await bus.unsubscribe(queue)


async def _push_events(websocket: ServerConnection, queue: asyncio.Queue[dict[str, Any]]) -> None:
    """从 EventBus Queue 推送事件到 WebSocket 客户端。"""
    try:
        while True:
            event = await queue.get()
            await websocket.send(json.dumps(event))
    except ConnectionClosed:
        return  # H-S3: 连接已关闭，优雅退出推送循环（不冒泡到 _handler）


async def _handle_commands(
    websocket: ServerConnection, bus: EventBus, snapshot_provider: Any = None,
) -> None:
    """接收并处理客户端控制命令。"""
    async for raw in websocket:
        try:
            cmd = json.loads(raw)
        except json.JSONDecodeError:
            await _send_response(websocket, False, "Invalid JSON")
            continue

        cmd_type = cmd.get("type")
        if cmd_type == "start_team":
            await _handle_start_team(cmd, websocket)
        elif cmd_type == "stop_team":
            await _handle_stop_team(cmd, websocket)
        elif cmd_type == "get_snapshot":
            await _handle_get_snapshot(cmd, websocket, snapshot_provider)
        else:
            await _send_response(websocket, False, f"Unknown command: {cmd_type}")


async def _handle_start_team(cmd: dict[str, Any], websocket: ServerConnection) -> None:
    """处理 start_team 控制命令（MVP：命令接收确认）。"""
    agent_cfg = cmd.get("agent", {})
    name = agent_cfg.get("name", "unknown")
    logger.info("start_team received for agent: %s", name)
    await _send_response(websocket, True)


async def _handle_stop_team(cmd: dict[str, Any], websocket: ServerConnection) -> None:
    """处理 stop_team 控制命令（MVP：取消对应 task）。"""
    name = cmd.get("name", "")
    task = _active_runners.pop(name, None)
    if task is not None:
        task.cancel()
        await _send_response(websocket, True)
    else:
        # H-S2: 无对应 runner 时诚实告知失败（_active_runners 当前恒空，
        # start_team 尚为 MVP 不填充，故 stop 永远走此分支——不再撒谎 success）
        await _send_response(websocket, False, "no active runner")


async def _handle_get_snapshot(
    cmd: dict[str, Any], websocket: ServerConnection, snapshot_provider: Any,
) -> None:
    """处理 get_snapshot 命令：重推会话 config/system_prompt 快照给请求客户端。"""
    if snapshot_provider is None:
        await _send_response(websocket, False, "snapshot not available")
        return
    session_id = cmd.get("session_id", "")
    events = snapshot_provider(session_id)
    if events is None:
        await _send_response(websocket, False, "session not found")
        return
    for event in events:
        await websocket.send(json.dumps(event))
    await _send_response(websocket, True)


async def _send_response(
    websocket: ServerConnection, success: bool, error: str | None = None,
) -> None:
    """发送 command_response 到客户端。"""
    response: dict[str, Any] = {"type": "command_response", "success": success}
    if error is not None:
        response["error"] = error
    await websocket.send(json.dumps(response))
