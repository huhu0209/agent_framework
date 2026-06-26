"""Chat 路由 — POST /chat (SSE), GET /chat/{id}。"""

from __future__ import annotations

import asyncio
import enum
import hmac
import json
import logging
import time
from typing import Any, AsyncGenerator

from pathlib import Path as FilePath

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request
from starlette.responses import StreamingResponse

from agent_framework.agents.agent_loop import LoopEvent
from agent_framework.viz.agent_runner import AgentRunner
from agent_framework.llm.base import (
    CircuitOpenError,
    LLMAdapterError,
    RateLimitError,
    ServiceUnavailableError,
)
from agent_framework.transcript import TranscriptConsumer
from app.models import SESSION_ID_RE, ChatRequest, HistoryResponse, RenameRequest
from app.services.session import _bucket_for

logger = logging.getLogger(__name__)


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    """A1: 校验 X-API-Key 头，恒定时间比较防时序攻击。"""
    settings = request.app.state.settings
    expected = settings.api_key.get_secret_value()
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


router = APIRouter(dependencies=[Depends(verify_api_key)])


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
        return ErrorCategory.LLM_TIMEOUT
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

    bucket = _bucket_for(req.project_path)
    working_dir: str | None = None
    if req.project_path is not None:
        resolved = FilePath(req.project_path).expanduser().resolve()
        if not resolved.is_dir():
            raise HTTPException(status_code=400, detail="project_path must be an existing directory")
        working_dir = str(resolved)

    sm = request.app.state.session_manager
    factory = request.app.state.agent_factory

    is_resume = False
    if req.session_id:
        # resume: agent_name 优先请求带的;若没带,回退到内存 session 绑定的 agent
        # (spec §6.2 session 级绑定 — 前端刷新后 currentChatAgent 丢失不应静默回退 default)
        effective_agent_name = req.agent_name
        if effective_agent_name is None:
            existing = sm.get(req.session_id)
            if existing is not None:
                effective_agent_name = existing.agent_name
        agent_loop = factory.create_loop(agent_name=effective_agent_name, working_dir=working_dir)
        session = await sm.get_or_restore(req.session_id, agent_loop, bucket=bucket)
        if session is None:
            raise HTTPException(404, "session not found")
        is_resume = True
    else:
        agent_loop = factory.create_loop(agent_name=req.agent_name, working_dir=working_dir)
        session = await sm.create(
            agent_loop, bucket=bucket, project_path=req.project_path,
            agent_name=req.agent_name,
        )

    # viz 事件层：构造 runner（bus 不可用时跳过，退回纯 SSE）
    bus = getattr(request.app.state, "bus", None)
    runner: AgentRunner | None = None
    if bus is not None:
        runner = AgentRunner(agent_loop, bus, session.session_id)
        session.agent_runner = runner

    session.messages.append({
        "role": "user",
        "content": req.message,
        "timestamp": time.time(),
    })
    await sm.persist_messages(session.session_id, session.messages, bucket=bucket)

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
            if runner is not None:
                gen = runner.wrap(gen)
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
                    await sm.persist_messages(session.session_id, session.messages, bucket=bucket)
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
                "content": _ERROR_MESSAGES[_classify_error(exc)],  # H-A3: 脱敏，与 SSE 一致
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
    bucket: str = Query("default_chat"),
    limit: int | None = Query(None, ge=1, le=500),  # H-A4: 上限防滥用
    before: str | None = Query(None),  # H-A4
) -> HistoryResponse:
    sm = request.app.state.session_manager
    before_ts: float | None = None
    if before is not None:
        try:
            before_ts = float(before)
        except (TypeError, ValueError):
            raise HTTPException(422, "before must be a numeric timestamp")  # H-A4
    result = await sm.get_messages(session_id, bucket=bucket, limit=limit, before=before_ts)
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
# GET /sessions/buckets — 列出所有桶(必须在 /sessions 之前定义,避免被
# /sessions/{session_id} 阴影匹配 "buckets")
# ---------------------------------------------------------------------------


@router.get("/sessions/buckets")
async def list_buckets(request: Request) -> list[dict]:
    """扫描 sessions/ 子目录,返回桶列表(default_chat 在前)。"""
    sm = request.app.state.session_manager
    storage = getattr(sm, "_storage_dir", None)
    if storage is None or not storage.exists():
        return [{"bucket": "default_chat", "display_name": "default_chat"}]
    buckets: list[dict] = []
    if (storage / "default_chat").exists():
        buckets.append({"bucket": "default_chat", "display_name": "default_chat"})
    for d in sorted(storage.iterdir()):
        if d.is_dir() and d.name != "default_chat":
            display = d.name.rsplit("_", 1)[0] if "_" in d.name else d.name
            buckets.append({"bucket": d.name, "display_name": display})
    return buckets


# ---------------------------------------------------------------------------
# GET /sessions — 列出历史会话
# ---------------------------------------------------------------------------

PREVIEW_SESSION_LIMIT = 10  # Only enrich the N most recent sessions to limit I/O


@router.get("/sessions/bucket-for")
async def bucket_for(project_path: str | None = Query(None)) -> dict:
    """返回 project_path 对应的桶名(供前端选项目后立即切桶)。"""
    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")
    resolved = FilePath(project_path).expanduser().resolve()
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="project_path must be an existing directory")
    bucket = _bucket_for(str(resolved))
    display = bucket.rsplit("_", 1)[0] if "_" in bucket else bucket
    return {"bucket": bucket, "display_name": display}


@router.get("/sessions")
async def list_sessions(
    request: Request,
    bucket: str = Query("default_chat"),
    preview: int = Query(0, ge=0, le=50),
    limit: int = Query(50, ge=1, le=200),  # H-A5: 分页
    offset: int = Query(0, ge=0),  # H-A5: 分页
) -> list[dict]:
    sm = request.app.state.session_manager
    sessions = await sm.list_sessions(bucket=bucket)
    paged = sessions[offset:offset + limit]  # H-A5: 分页切片
    if preview <= 0:
        return paged
    # H-A5: 并发 enrichment 前 PREVIEW_SESSION_LIMIT 个（替代串行 N+1）
    enrich_count = min(PREVIEW_SESSION_LIMIT, len(paged))

    async def enrich(session: dict) -> dict:
        new_session = {**session}
        msgs = await sm.get_messages(session["session_id"], limit=preview)
        if msgs is not None:
            messages, has_more, _ = msgs
            new_session["preview"] = messages
            if has_more:
                count = await sm.count_messages(session["session_id"])
                new_session["message_count"] = count if count is not None else len(messages)
            else:
                new_session["message_count"] = len(messages)
        else:
            new_session["preview"] = None
        return new_session

    enriched = await asyncio.gather(*[enrich(s) for s in paged[:enrich_count]])
    rest = [{**s, "preview": None} for s in paged[enrich_count:]]
    return list(enriched) + rest


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id} — 删除会话
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}")
async def delete_session(
    request: Request,
    session_id: str = Path(pattern=SESSION_ID_RE.pattern),
    bucket: str = Query("default_chat"),
) -> dict:
    sm = request.app.state.session_manager
    deleted = await sm.delete_session(session_id, bucket=bucket)
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
    bucket: str = Query("default_chat"),
    req: RenameRequest = ...,  # body — required
) -> dict:
    sm = request.app.state.session_manager
    updated = await sm.update_title(session_id, req.title, bucket=bucket)
    if not updated:
        raise HTTPException(404, "session not found")
    return {"status": "ok"}
