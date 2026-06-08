"""Agent Chat 后端 — FastAPI 入口。"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.config import Settings
from app.services.agent_factory import AgentFactory
from app.services.session import SessionManager

logging.basicConfig(level=logging.INFO)

ALLOWED_ORIGINS = os.getenv("APP_CORS_ORIGINS", "http://localhost:30001").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    factory = AgentFactory.from_settings(settings)
    sm = SessionManager()
    sm.start_cleanup()

    app.state.session_manager = sm
    app.state.agent_factory = factory
    yield
    sm.cancel_all()
    sm.stop_cleanup()


app = FastAPI(title="Agent Chat", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router, prefix="/api/v1")
