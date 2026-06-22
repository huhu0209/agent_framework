"""VizEvent 数据模型 — Agent 可视化事件的标准化表示。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

VizEventType = Literal[
    "idle", "thinking", "tool_call", "tool_result",
    "done", "error", "shutdown",
    "config", "system_prompt", "memory",
    "usage",
]


class PromptBlockPayload(BaseModel):
    """system prompt 组成块的序列化结构（对应 PromptAssembler.PromptBlock）。"""

    name: str
    content: str
    source: Literal["file", "auto_generated", "injected"]
    stability: Literal["static", "semi_static", "dynamic"]


class SystemPromptPayload(BaseModel):
    """system_prompt 事件的 payload 契约。"""

    text: str
    blocks: list[PromptBlockPayload] = []


class ConfigPayload(BaseModel):
    """config 事件的 payload 契约。"""

    model: str
    max_steps: int
    profile: str | None = None
    permission_mode: str | None = None
    tools: list[str] = []


class UsagePayload(BaseModel):
    """usage 事件的 payload 契约 — 单步与 session 累计 token 用量 + 模型上限。

    - input/output:最近一次单步 LLM 调用的 token(input 即当前上下文大小)
    - cumulative_input/output:当前会话累计 token
    - max_context:模型(provider)上下文上限,随每次事件携带
    """

    input: int
    output: int
    cumulative_input: int
    cumulative_output: int
    max_context: int


class VizEvent(BaseModel):
    """前端可视化的 Agent 执行事件。

    payload 保持 dict[str, Any] 以兼容现有 tool/thinking 等事件的裸 dict 消费
    （agent_runner._make_viz 与 ws_server 的 json.dumps(model_dump)）。
    ConfigPayload / SystemPromptPayload 作为类型化契约供生产侧构造与测试校验，
    不强制为 payload 的 Union 成员（否则会破坏现有 tool_call/thinking payload 解析）。
    """

    type: VizEventType
    agent: str
    session_id: str = ""
    payload: dict[str, Any]
    timestamp: float
