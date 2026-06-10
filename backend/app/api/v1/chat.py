"""Chat 路由 — POST /chat (SSE), GET /chat/{id}。"""

from __future__ import annotations

import asyncio
import enum
import json
import logging
import time
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Path, Request
from starlette.responses import StreamingResponse

from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.llm.base import (
    CircuitOpenError,
    LLMAdapterError,
    RateLimitError,
    ServiceUnavailableError,
)
from agent_framework.transcript import TranscriptConsumer
from app.models import SESSION_ID_RE, ChatRequest, HistoryResponse, RenameRequest

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Error classification (BK-SEC-01)
# ---------------------------------------------------------------------------


class ErrorCategory(enum.Enum):
    """SSE 错误分类 — 客户端收到用户友好消息，不泄露内部信息。"""

    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    TOOL_ERROR = "tool_error"
    SESSION_NOT_FOUND = "session_not_found"
    UNKNOWN_ERROR = "unknown_error"


_ERROR_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.LLM_TIMEOUT: "AI 服务响应超时，请稍后重试。",
    ErrorCategory.LLM_RATE_LIMIT: "AI 服务繁忙，请稍后重试。",
    ErrorCategory.TOOL_ERROR: "工具执行出错，请检查输入。",
    ErrorCategory.SESSION_NOT_FOUND: "会话不存在或已过期。",
    ErrorCategory.UNKNOWN_ERROR: "服务内部错误，请稍后重试。",
}


def _classify_error(exc: Exception) -> ErrorCategory:
    """将异常类型映射到 ErrorCategory（D-03）。"""
    if isinstance(exc, RateLimitError):
        return ErrorCategory.LLM_RATE_LIMIT
    if isinstance(exc, (ServiceUnavailableError, CircuitOpenError)):
        return ErrorCategory.LLM_TIMEOUT
    if isinstance(exc, LLMAdapterError):
        return ErrorCategory.LLM_TIMEOUT
    if isinstance(exc, asyncio.TimeoutError):
        return ErrorCategory.TOOL_ERROR
    return ErrorCategory.UNKNOWN_ERROR


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(event_name: str, payload: dict[str, Any]) -> str:
    """格式化单条 SSE 事件。"""
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


def _map_to_sse(event: LoopEvent) -> list[str]:
    """将 LoopEvent 映射为零或多条 SSE 事件字符串。"""
    event_type = event.type
    data = event.data

    if event_type == "step":
        stop_reason = data.get("stop_reason")
        if stop_reason == "tool_use":
            return [_sse("thinking", {"step": event.step, **data})]
        if stop_reason in ("end_turn", "stop_sequence"):
            return []
        return []

    if event_type == "tool_result":
        results: list[str] = []
        tool_calls = data.get("tool_calls", [])
        tool_results_raw = data.get("tool_results", [])
        for i, tc in enumerate(tool_calls):
            result_content = tool_results_raw[i] if i < len(tool_results_raw) else ""
            results.append(_sse("tool_call", {
                "step": event.step,
                "tool_call_id": tc.get("id", ""),
                "tool_name": tc.get("name", ""),
                "params": tc.get("input", {}),
            }))
            results.append(_sse("tool_result", {
                "step": event.step,
                "tool_call_id": tc.get("id", ""),
                "tool_name": tc.get("name", ""),
                "content": result_content,
            }))
        return results

    if event_type == "done":
        return [_sse("done", {"step": event.step, **data})]

    if event_type in ("error", "max_steps"):
        return [_sse("error", {"step": event.step, **data})]

    return []


# ---------------------------------------------------------------------------
# POST /chat — SSE streaming
# ---------------------------------------------------------------------------

@router.post("/chat")
async def create_chat(req: ChatRequest, request: Request):
    if not req.message.strip():
        raise HTTPException(400, "message is required")

    sm = request.app.state.session_manager
    factory = request.app.state.agent_factory

    is_resume = False
    if req.session_id:
        agent_loop = factory.create_loop()
        session = await sm.get_or_restore(req.session_id, agent_loop)
        if session is None:
            raise HTTPException(404, "session not found")
        is_resume = True
    else:
        agent_loop = factory.create_loop()
        session = await sm.create(agent_loop)

    session.messages.append({
        "role": "user",
        "content": req.message,
        "timestamp": time.time(),
    })
    await sm.persist_messages(session.session_id, session.messages)

    async def event_stream() -> AsyncGenerator[str, None]:
        loop = session.agent_loop
        if loop is None:
            yield _sse("error", {"error": "No agent loop"})
            yield _sse("shutdown", {})
            return
        try:
            gen = loop.run(req.message, resume=is_resume)
            if session.transcript_writer is not None:
                consumer = TranscriptConsumer(
                    session.transcript_writer,
                    system_prompt=loop.system_prompt_text,
                )
                gen = consumer.wrap(gen, req.message)
            async for loop_event in gen:
                for sse_line in _map_to_sse(loop_event):
                    yield sse_line
                if loop_event.type == "done":
                    content = loop_event.data.get("content", [])
                    session.messages.append({
                        "role": "agent",
                        "blocks": content,
                        "timestamp": time.time(),
                    })
                    await sm.persist_messages(session.session_id, session.messages)
                    # 更新会话标题（取第一条用户消息前 50 字符）
                    if len(session.messages) <= 2:
                        await sm.update_title(session.session_id, req.message[:50])
        except Exception as exc:
            logger.exception("Agent error in session %s", session.session_id)
            yield _sse("error", {
                "step": 0,
                "error": _ERROR_MESSAGES[_classify_error(exc)],
            })
            session.messages.append({
                "role": "error",
                "content": str(exc),
                "timestamp": time.time(),
            })
        finally:
            yield _sse("shutdown", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Session-Id": session.session_id},
    )


# ---------------------------------------------------------------------------
# GET /chat/{id} — 历史查询（不变）
# ---------------------------------------------------------------------------

@router.get("/chat/{session_id}", response_model=HistoryResponse)
async def get_history(
    request: Request,
    session_id: str = Path(pattern=SESSION_ID_RE.pattern),
    limit: int | None = None,
    before: str | None = None,
) -> HistoryResponse:
    sm = request.app.state.session_manager
    before_ts = float(before) if before else None
    result = await sm.get_messages(session_id, limit=limit, before=before_ts)
    if result is None:
        raise HTTPException(404, "session not found")
    messages, has_more, next_cursor = result
    return HistoryResponse(
        session_id=session_id,
        messages=messages,
        has_more=has_more,
        next_cursor=next_cursor,
    )


# ---------------------------------------------------------------------------
# GET /sessions — 列出历史会话
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(request: Request) -> list[dict]:
    sm = request.app.state.session_manager
    return await sm.list_sessions()


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id} — 删除会话
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}")
async def delete_session(
    request: Request,
    session_id: str = Path(pattern=SESSION_ID_RE.pattern),
) -> dict:
    sm = request.app.state.session_manager
    deleted = await sm.delete_session(session_id)
    if not deleted:
        raise HTTPException(404, "session not found")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# PATCH /sessions/{session_id} — 重命名会话
# ---------------------------------------------------------------------------

@router.patch("/sessions/{session_id}")
async def rename_session(
    request: Request,
    session_id: str = Path(pattern=SESSION_ID_RE.pattern),
    req: RenameRequest = ...,  # body — required
) -> dict:
    sm = request.app.state.session_manager
    updated = await sm.update_title(session_id, req.title)
    if not updated:
        raise HTTPException(404, "session not found")
    return {"status": "ok"}
