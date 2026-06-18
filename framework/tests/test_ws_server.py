"""WebSocket 服务端集成测试 — WSRV-01~05。"""

import asyncio
import json
import socket

import pytest
from websockets.asyncio.client import connect

from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.ws_server import serve_ws


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
async def ws_server():
    bus = EventBus()
    port = _free_port()
    task = asyncio.create_task(serve_ws(bus, port=port))
    # brief sleep to let server bind
    await asyncio.sleep(0.05)
    yield bus, port, task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_client_receives_viz_events(ws_server: tuple) -> None:
    bus, port, _ = ws_server
    event = {"type": "thinking", "agent": "cat", "payload": {}, "timestamp": 1.0}

    async with connect(f"ws://localhost:{port}") as ws:
        await bus.publish(event)
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(raw)
        assert data["type"] == "thinking"
        assert data["agent"] == "cat"


async def test_disconnect_unsubscribes(ws_server: tuple) -> None:
    bus, port, _ = ws_server

    async with connect(f"ws://localhost:{port}"):
        assert bus.subscriber_count == 1

    await asyncio.sleep(0.1)
    assert bus.subscriber_count == 0


async def test_start_team_command(ws_server: tuple) -> None:
    _, port, _ = ws_server

    async with connect(f"ws://localhost:{port}") as ws:
        cmd = {"type": "start_team", "agent": {"name": "cat", "role": "helper", "system_prompt": "test"}}
        await ws.send(json.dumps(cmd))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["type"] == "command_response"
        assert resp["success"] is True


async def test_stop_team_command(ws_server: tuple) -> None:
    """H-S2: stop_team 无对应 active runner 时返回 success=False（诚实响应，不撒谎）。"""
    _, port, _ = ws_server

    async with connect(f"ws://localhost:{port}") as ws:
        cmd = {"type": "stop_team", "name": "cat"}
        await ws.send(json.dumps(cmd))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["type"] == "command_response"
        assert resp["success"] is False  # H-S2: 无 active runner，不再撒谎成功
        assert "no active runner" in resp["error"]


async def test_unknown_command_returns_error(ws_server: tuple) -> None:
    _, port, _ = ws_server

    async with connect(f"ws://localhost:{port}") as ws:
        await ws.send(json.dumps({"type": "unknown"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["success"] is False
        assert "Unknown command" in resp["error"]


async def test_malformed_json_returns_error(ws_server: tuple) -> None:
    _, port, _ = ws_server

    async with connect(f"ws://localhost:{port}") as ws:
        await ws.send("not json")
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["success"] is False
        assert "Invalid JSON" in resp["error"]


async def test_multiple_clients_receive_events(ws_server: tuple) -> None:
    bus, port, _ = ws_server
    event = {"type": "done", "agent": "cat", "payload": {}, "timestamp": 2.0}

    async with connect(f"ws://localhost:{port}") as ws1, \
            connect(f"ws://localhost:{port}") as ws2:
        await bus.publish(event)
        r1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
        r2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
        assert r1["type"] == "done"
        assert r2["type"] == "done"


# --- Token authentication tests ---


@pytest.fixture
async def ws_server_with_token():
    bus = EventBus()
    port = _free_port()
    task = asyncio.create_task(serve_ws(bus, port=port, token="secret123"))
    await asyncio.sleep(0.05)
    yield bus, port, task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_valid_token_connects_successfully(ws_server_with_token: tuple) -> None:
    _, port, _ = ws_server_with_token

    async with connect(f"ws://localhost:{port}?token=secret123") as ws:
        # Connection should succeed — send a ping-like command
        await ws.send(json.dumps({"type": "unknown"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["success"] is False  # unknown command, but connection works
        assert "Unknown command" in resp["error"]


async def test_invalid_token_rejected(ws_server_with_token: tuple) -> None:
    _, port, _ = ws_server_with_token

    async with connect(f"ws://localhost:{port}?token=wrong") as ws:
        # Server closes after handshake; client discovers on recv
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2.0)


async def test_missing_token_when_required_rejected(ws_server_with_token: tuple) -> None:
    _, port, _ = ws_server_with_token

    async with connect(f"ws://localhost:{port}") as ws:
        # Server closes after handshake; client discovers on recv
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2.0)


async def test_no_auth_mode_accepts_all(ws_server: tuple) -> None:
    """Default fixture (no token) accepts connections without query params."""
    bus, port, _ = ws_server
    event = {"type": "done", "agent": "cat", "payload": {}, "timestamp": 1.0}

    async with connect(f"ws://localhost:{port}") as ws:
        await bus.publish(event)
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(raw)
        assert data["type"] == "done"


# --- B4: Origin validation (CSWSH) + production token gate ---


@pytest.fixture
async def ws_server_with_origins():
    bus = EventBus()
    port = _free_port()
    task = asyncio.create_task(
        serve_ws(bus, port=port, allowed_origins=["http://localhost:5173"])
    )
    await asyncio.sleep(0.05)
    yield bus, port, task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_origin_in_allowlist_accepted(ws_server_with_origins: tuple) -> None:
    """B4: 白名单内 Origin 可正常连接。"""
    _, port, _ = ws_server_with_origins
    async with connect(
        f"ws://localhost:{port}", additional_headers={"Origin": "http://localhost:5173"}
    ) as ws:
        await ws.send(json.dumps({"type": "unknown"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["success"] is False  # unknown command，但连接成功
        assert "Unknown command" in resp["error"]


async def test_origin_not_in_allowlist_rejected(ws_server_with_origins: tuple) -> None:
    """B4: 非白名单 Origin 连接被拒（CSWSH 防护）。"""
    _, port, _ = ws_server_with_origins
    async with connect(
        f"ws://localhost:{port}", additional_headers={"Origin": "http://evil.example.com"}
    ) as ws:
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2.0)


async def test_origin_missing_rejected(ws_server_with_origins: tuple) -> None:
    """B4: allowed_origins 已设置时，缺 Origin 头的连接被拒（fail-closed）。"""
    _, port, _ = ws_server_with_origins
    async with connect(f"ws://localhost:{port}") as ws:  # 不带 Origin 头
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2.0)


async def test_production_without_token_raises() -> None:
    """B4: 生产模式 token=None 拒绝启动（fail-safe）。"""
    bus = EventBus()
    port = _free_port()
    with pytest.raises(ValueError, match="token"):
        await serve_ws(bus, port=port, production=True, token=None)


async def test_production_with_token_starts() -> None:
    """B4: 生产模式 + token 正常启动（不抛）。"""
    bus = EventBus()
    port = _free_port()
    task = asyncio.create_task(
        serve_ws(bus, port=port, production=True, token="prod-secret")
    )
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # 到这里即说明未在启动阶段抛错


# --- H-S3: _push_events 捕获 ConnectionClosed ---


async def test_push_events_swallows_connection_closed() -> None:
    """H-S3: _push_events 在 websocket.send 抛 ConnectionClosed 时优雅退出，不冒泡。"""
    from agent_framework.viz.ws_server import _push_events
    from websockets.exceptions import ConnectionClosed

    class FakeWS:
        async def send(self, data: str) -> None:
            raise ConnectionClosed(None, None)

    queue: asyncio.Queue = asyncio.Queue()
    queue.put_nowait({"type": "done", "agent": "cat", "payload": {}, "timestamp": 1.0})

    # 修复前：ConnectionClosed 冒泡抛出
    # 修复后：优雅 return，不抛
    await _push_events(FakeWS(), queue)  # 不应 raise
