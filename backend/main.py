"""Agent Chat 后端 — FastAPI 入口。"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import redis as redis_lib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_framework.config.loader import ConfigLoader
from agent_framework.viz.event_bus import EventBus
from agent_framework.viz.recorder import RecordingSubscriber
from agent_framework.viz.ws_server import serve_ws

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

    # --- 初始化 Agent 工厂（APP_AGENT_BACKEND=stub 时用 E2E stub，免真实 LLM）---
    if os.getenv("APP_AGENT_BACKEND") == "stub":
        from app.services.stub_factory import StubAgentFactory
        factory = StubAgentFactory()
        logger.warning("APP_AGENT_BACKEND=stub: using StubAgentFactory (E2E only, never production)")
    else:
        factory = AgentFactory.from_configloader(config_loader, settings)

    # --- 连接 Redis（可选，失败时降级为本地文件存储）---
    rdb = None
    try:
        rdb = redis_lib.asyncio.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,  # 主动探测 stale 连接，提前换掉坏连接（和 try/except 降级互补）
        )  # H-A1: async
        await rdb.ping()
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

    # --- viz 事件总线 + WebSocket 服务（失败降级，不影响 SSE 聊天）---
    app.state.bus = EventBus()

    def _on_ws_done(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.warning(
                "viz WebSocket server stopped: %s. Inspector offline, chat unaffected.", exc,
            )

    app.state.ws_task = None
    if settings.ws_enabled:
        ws_token = settings.ws_token.get_secret_value() or None

        def _snapshot_provider(session_id: str) -> list[dict] | None:
            """重推会话快照：优先 recorder 全量回放（含工具链），无录制时内存兜底。

            全量回放覆盖"历史 session 工具链被挤出 EventBus 200 条窗口"的场景：
            前端晚连接/回看时，工具链也能从 jsonl 完整恢复。
            """
            rec = getattr(app.state, "viz_recorder", None)
            if rec is not None:
                replay = rec.read_replay(session_id)
                if replay:
                    return replay  # 全量：config/prompt/工具链
            # 录制文件还没有（新 session 首条消息尚未落盘）：从内存 emit config/prompt
            session = sm.get(session_id)
            if session is not None and session.agent_runner is not None:
                return session.agent_runner.emit_snapshot()
            return None

        app.state.ws_task = asyncio.create_task(
            serve_ws(
                app.state.bus,
                host=settings.ws_host,
                port=settings.ws_port,
                token=ws_token,
                allowed_origins=settings.ws_cors_origins,
                snapshot_provider=_snapshot_provider,
            )
        )
        app.state.ws_task.add_done_callback(_on_ws_done)
        logger.info(
            "viz WebSocket server starting on ws://%s:%d", settings.ws_host, settings.ws_port,
        )

    # --- viz 事件录制（回放种子，按 session 落盘）---
    viz_storage = Path(__file__).parent / "data" / "viz_events"
    recorder = RecordingSubscriber(app.state.bus, viz_storage)
    await recorder.start()
    app.state.viz_recorder = recorder

    yield  # 应用运行中

    # --- 应用关闭时清理资源 ---
    sm.cancel_all()
    sm.stop_cleanup()
    if rdb:
        await rdb.aclose()  # H-A1: async

    ws_task = getattr(app.state, "ws_task", None)
    if ws_task is not None and not ws_task.done():
        ws_task.cancel()
        try:
            await ws_task
        except (asyncio.CancelledError, Exception):
            pass

    recorder = getattr(app.state, "viz_recorder", None)
    if recorder is not None:
        await recorder.stop()


app = FastAPI(title="Agent Chat", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "X-Session-Id", "X-API-Key"],  # A1/A3: 加 X-API-Key
    expose_headers=["X-Session-Id"],  # 前端跨域读 X-Session-Id(connectInspector 启动拉 config 依赖)
)
app.include_router(chat_router, prefix="/api/v1")
