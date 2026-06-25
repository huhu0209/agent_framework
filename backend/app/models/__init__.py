"""请求/响应数据模型。"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# ChatRequest.message 长度上限（与 Settings.max_message_length 对齐，防超长消息 DoS）
MAX_MESSAGE_LENGTH = 8000


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=MAX_MESSAGE_LENGTH)
    session_id: str | None = None
    project_path: str | None = None
    agent_name: str | None = None  # 选用哪个具名 agent;None=默认

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        """验证是否为 32位十六进制小写字符串（即标准 UUID 去掉连字符的格式）"""
        if v is not None and not SESSION_ID_RE.match(v):
            raise ValueError("invalid session_id format")
        return v

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v: str | None) -> str | None:
        """空白字符串归一化为 None"""
        if v is not None and not v.strip():
            return None
        return v


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str
    timestamp: float


class AgentMessage(BaseModel):
    role: Literal["agent"] = "agent"
    blocks: list[dict]
    timestamp: float


class ErrorMessage(BaseModel):
    role: Literal["error"] = "error"
    content: str
    timestamp: float


Message = UserMessage | AgentMessage | ErrorMessage


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[Message]
    has_more: bool = False
    next_cursor: str | None = None


class RenameRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        if len(v) > 100:
            raise ValueError("title too long (max 100)")
        return v
