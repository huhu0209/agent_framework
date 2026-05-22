"""HITL — Human-in-the-Loop 同步权限交互。"""

from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel

from agent_framework.safety.permissions import RiskLevel


class PermissionOption(BaseModel):
    """给用户的选择项。"""

    action: Literal["approve", "approve_once", "approve_session", "deny"]
    label: str


class PermissionRequest(BaseModel):
    """权限请求。"""

    request_id: str
    tool_name: str
    tool_input: dict
    reason: str
    risk_level: RiskLevel
    options: list[PermissionOption]


class PermissionResponse(BaseModel):
    """用户对权限请求的回应。"""

    request_id: str
    action: str
    modified_input: dict | None = None


class HITLManager:
    """管理待处理的权限请求。"""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[PermissionResponse]] = {}

    def create_pending(self, request: PermissionRequest) -> asyncio.Future[PermissionResponse]:
        """创建一个待处理的权限请求，返回 Future。"""
        loop = asyncio.get_event_loop()
        future: asyncio.Future[PermissionResponse] = loop.create_future()
        self._pending[request.request_id] = future
        return future

    def resolve(self, request_id: str, response: PermissionResponse) -> None:
        """解决一个待处理的权限请求。"""
        future = self._pending.get(request_id)
        if future is None:
            raise KeyError(f"未知的权限请求: {request_id}")
        future.set_result(response)
        del self._pending[request_id]

    def cancel_all(self) -> None:
        """取消所有待处理请求。"""
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
