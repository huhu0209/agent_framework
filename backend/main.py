"""Agent Chat 后端 — FastAPI 入口。"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import redis as redis_lib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.config import Settings
from app.services.agent_factory import AgentFactory
from app.services.session import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv("APP_CORS_ORIGINS", "http://localhost:30001").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 读取配置 ---
    settings = Settings()

    # --- 初始化 Agent 工厂 ---
    factory = AgentFactory.from_settings(settings)

    # --- 连接 Redis（可选，失败时降级为本地文件存储）---
    rdb = None
    try:
        rdb = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
        rdb.ping()
    except Exception:
        logger.warning("Redis unavailable, caching disabled")
        rdb = None

    # --- 初始化会话管理器，启动定期清理任务 ---
    storage_dir = Path(__file__).parent / "data" / "sessions"
    sm = SessionManager(storage_dir=storage_dir, redis_client=rdb)
    sm.start_cleanup()

    # --- 挂载到 app.state，供各路由通过 request.app.state 访问 ---
    app.state.session_manager = sm
    app.state.agent_factory = factory

    yield  # 应用运行中

    # --- 应用关闭时清理资源 ---
    sm.cancel_all()
    sm.stop_cleanup()
    if rdb:
        rdb.close()


app = FastAPI(title="Agent Chat", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router, prefix="/api/v1")
