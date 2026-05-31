"""VizEvent 数据模型 — Agent 可视化事件的标准化表示。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

VizEventType = Literal["idle", "thinking", "tool_call", "done", "error", "shutdown"]


class VizEvent(BaseModel):
    """前端可视化的 Agent 执行事件。"""

    type: VizEventType
    agent: str
    payload: dict[str, Any]
    timestamp: float
