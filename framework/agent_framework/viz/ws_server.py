"""WebSocket 服务端 — 订阅 EventBus 推送 VizEvent + 处理控制命令。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.server import ServerConnection, serve

from agent_framework.viz.event_bus import EventBus

logger = logging.getLogger(__name__)

_active_runners: dict[str, asyncio.Task[None]] = {}


async def serve_ws(bus: EventBus, host: str = "localhost", port: int = 8765) -> None:
    """启动 WebSocket 服务端。"""

    async with serve(lambda ws: _handler(ws, bus), host, port) as server:
        logger.info("WebSocket server listening on ws://%s:%d", host, port)
        await server.wait_closed()


async def _handler(websocket: ServerConnection, bus: EventBus) -> None:
    """处理单个 WebSocket 连接：推送事件 + 接收命令。"""
    queue = await bus.subscribe()
    try:
        recv_task = asyncio.create_task(_handle_commands(websocket, bus))
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
                pass
    finally:
        await bus.unsubscribe(queue)


async def _push_events(websocket: ServerConnection, queue: asyncio.Queue[dict[str, Any]]) -> None:
    """从 EventBus Queue 推送事件到 WebSocket 客户端。"""
    while True:
        event = await queue.get()
        await websocket.send(json.dumps(event))


async def _handle_commands(websocket: ServerConnection, bus: EventBus) -> None:
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


async def _send_response(
    websocket: ServerConnection, success: bool, error: str | None = None,
) -> None:
    """发送 command_response 到客户端。"""
    response: dict[str, Any] = {"type": "command_response", "success": success}
    if error is not None:
        response["error"] = error
    await websocket.send(json.dumps(response))
