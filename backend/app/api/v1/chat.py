"""Chat 路由 — POST /chat (SSE), GET /chat/{id}。"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import StreamingResponse

from agent_framework.agents.agent_loop import LoopEvent
from app.models import ChatRequest, HistoryResponse
from app.services.session import ChatSession

logger = logging.getLogger(__name__)

router = APIRouter()


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
            return [_sse("done", {"step": event.step, **data})]
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
        session = sm.get(req.session_id)
        if session is None:
            raise HTTPException(404, "session not found")
        is_resume = True
    else:
        agent_loop = factory.create_loop()
        session = sm.create(agent_loop)

    session.messages.append({
        "role": "user",
        "content": req.message,
        "timestamp": time.time(),
    })

    async def event_stream() -> AsyncGenerator[str, None]:
        loop = session.agent_loop
        if loop is None:
            yield _sse("error", {"error": "No agent loop"})
            yield _sse("shutdown", {})
            return
        try:
            async for loop_event in loop.run(req.message, resume=is_resume):
                for sse_line in _map_to_sse(loop_event):
                    yield sse_line
                if loop_event.type == "done":
                    content = loop_event.data.get("content", [])
                    session.messages.append({
                        "role": "agent",
                        "blocks": content,
                        "timestamp": time.time(),
                    })
        except Exception as exc:
            logger.exception("Agent error in session %s", session.session_id)
            yield _sse("error", {"error": str(exc)})
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
async def get_history(session_id: str, request: Request) -> HistoryResponse:
    sm = request.app.state.session_manager
    session = sm.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return HistoryResponse(session_id=session.session_id, messages=session.messages)
