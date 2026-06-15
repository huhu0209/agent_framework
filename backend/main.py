"""Agent Chat 后端 — FastAPI 入口。"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import redis as redis_lib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_framework.config.loader import ConfigLoader

from app.api.v1.chat import router as chat_router
from app.config import Settings, create_settings
from app.services.agent_factory import AgentFactory
from app.services.session import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_cors_origins(origins: list[str]) -> None:
    """A3: allow_credentials=True 时禁止 '*'，否则任意源可携凭据访问。"""
    if "*" in origins:
        raise ValueError(
            "ALLOWED_ORIGINS must not contain '*' when allow_credentials=True"
        )


ALLOWED_ORIGINS = [o.strip() for o in os.getenv("APP_CORS_ORIGINS", "http://localhost:30001").split(",") if o.strip()]
validate_cors_origins(ALLOWED_ORIGINS)  # A3: 启动时校验


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- ConfigLoader first per D-01（提供回退默认值）---
    # project_dir 指向项目根目录（backend/ 的父目录），而非 CWD
    project_root = Path(__file__).resolve().parent.parent
    config_loader = ConfigLoader(project_dir=project_root)
    fw_settings = config_loader.load_settings()

    # --- Backend Settings with ConfigLoader fallback, env vars still highest priority per D-01 ---
    settings = create_settings(framework_settings=fw_settings)
    app.state.settings = settings  # 供 verify_api_key 依赖读取

    # --- 初始化 Agent 工厂 ---
    factory = AgentFactory.from_configloader(config_loader, settings)

    # --- 连接 Redis（可选，失败时降级为本地文件存储）---
    rdb = None
    try:
        rdb = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
        rdb.ping()
    except (redis_lib.ConnectionError, redis_lib.TimeoutError) as exc:
        logger.error("Redis connection failed: %s. Caching disabled.", exc)
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
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "X-Session-Id", "X-API-Key"],  # A1/A3: 加 X-API-Key
)
app.include_router(chat_router, prefix="/api/v1")
