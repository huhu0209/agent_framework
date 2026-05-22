"""HITL 数据模型测试。"""

import asyncio

import pytest

from agent_framework.safety.hitl import (
    HITLManager,
    PermissionOption,
    PermissionRequest,
    PermissionResponse,
    RiskLevel,
)


class TestPermissionRequest:
    def test_create_request(self):
        req = PermissionRequest(
            request_id="test-123",
            tool_name="write_file",
            tool_input={"path": "/etc/passwd", "content": "hacked"},
            reason="destructive operation",
            risk_level=RiskLevel.HIGH,
            options=[
                PermissionOption(action="approve_once", label="允许本次"),
                PermissionOption(action="deny", label="拒绝"),
            ],
        )
        assert req.request_id == "test-123"
        assert req.risk_level == RiskLevel.HIGH
        assert len(req.options) == 2


class TestPermissionResponse:
    def test_approve_response(self):
        resp = PermissionResponse(request_id="test-123", action="approve_once")
        assert resp.action == "approve_once"
        assert resp.modified_input is None

    def test_modify_response(self):
        resp = PermissionResponse(
            request_id="test-123",
            action="approve_once",
            modified_input={"path": "/safe/path.txt"},
        )
        assert resp.modified_input["path"] == "/safe/path.txt"


class TestHITLManager:
    def test_create_and_resolve(self):
        async def _test():
            manager = HITLManager()
            req = PermissionRequest(
                request_id="req-1",
                tool_name="write_file",
                tool_input={"path": "test.txt"},
                reason="test",
                risk_level=RiskLevel.LOW,
                options=[],
            )

            future = manager.create_pending(req)
            assert not future.done()

            manager.resolve("req-1", PermissionResponse(request_id="req-1", action="approve_once"))
            assert future.done()
            result = future.result()
            assert result.action == "approve_once"

        asyncio.run(_test())

    def test_resolve_unknown_id_raises(self):
        async def _test():
            manager = HITLManager()
            with pytest.raises(KeyError):
                manager.resolve("unknown", PermissionResponse(request_id="unknown", action="deny"))

        asyncio.run(_test())

    def test_cancel_all(self):
        async def _test():
            manager = HITLManager()
            req = PermissionRequest(
                request_id="req-1",
                tool_name="write_file",
                tool_input={},
                reason="test",
                risk_level=RiskLevel.LOW,
                options=[],
            )

            future = manager.create_pending(req)
            manager.cancel_all()
            assert future.cancelled()

        asyncio.run(_test())
