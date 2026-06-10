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
    _, port, _ = ws_server

    async with connect(f"ws://localhost:{port}") as ws:
        cmd = {"type": "stop_team", "name": "cat"}
        await ws.send(json.dumps(cmd))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["type"] == "command_response"
        assert resp["success"] is True


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
