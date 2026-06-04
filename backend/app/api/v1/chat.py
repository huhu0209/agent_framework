"""Chat 路由 — POST /chat, GET /chat/{id}, WS /ws/{id}。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from agent_framework.viz.agent_runner import AgentRunner
from app.models import ChatRequest, ChatResponse, HistoryResponse
from app.services.session import ChatSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, status_code=201)
async def create_chat(req: ChatRequest, request: Request) -> ChatResponse:
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

    task = asyncio.create_task(
        _run_agent(session, req.message, is_resume),
    )
    sm.replace_task(session, task)

    return ChatResponse(session_id=session.session_id)


@router.get("/chat/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str, request: Request) -> HistoryResponse:
    sm = request.app.state.session_manager
    session = sm.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return HistoryResponse(session_id=session.session_id, messages=session.messages)


@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    sm = websocket.app.state.session_manager
    session = sm.get(session_id)
    if session is None:
        await websocket.close(code=4404, reason="session not found")
        return

    queue = await session.bus.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("WS disconnected: %s", session_id)
    finally:
        await session.bus.unsubscribe(queue)


async def _run_agent(
    session: ChatSession,
    user_message: str,
    is_resume: bool,
) -> None:
    loop = session.agent_loop
    if loop is None:
        logger.error("Session %s has no agent_loop", session.session_id)
        return

    runner = AgentRunner("Agent", session.bus)

    try:
        async for loop_event in runner.wrap(loop.run(user_message, resume=is_resume)):
            if loop_event.type == "done":
                content = loop_event.data.get("content", [])
                session.messages.append({
                    "role": "agent",
                    "blocks": content,
                    "timestamp": time.time(),
                })
    except Exception as exc:
        logger.exception("Agent error in session %s", session.session_id)
        error_msg = {
            "type": "error",
            "data": {"message": f"Agent error: {exc}"},
        }
        await session.bus.publish(error_msg)
        session.messages.append({
            "role": "error",
            "content": str(exc),
            "timestamp": time.time(),
        })
