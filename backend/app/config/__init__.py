"""应用配置 — 从环境变量 / .env 读取，支持 ConfigLoader 回退。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from agent_framework.config.settings import Settings as FrameworkSettings


class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "claude-sonnet-4-20250514"
    llm_base_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    api_key: SecretStr = SecretStr("")  # 后端 API 鉴权 key（env APP_API_KEY）
    max_message_length: int = 8000  # ChatRequest.message 长度上限（与 models.MAX_MESSAGE_LENGTH 对齐）

    # viz WebSocket 观测面板配置（env 前缀 APP_，如 APP_WS_TOKEN）
    ws_enabled: bool = True
    ws_host: str = "localhost"
    ws_port: int = 8765
    ws_token: SecretStr = SecretStr("")  # 空 → 无 auth（仅开发态）；生产必须设置
    ws_cors_origins: list[str] = ["http://localhost:30001", "http://localhost:5173"]  # 前端 dev server Origin 白名单（vite 实际 30001 + 默认 5173）

    model_config = {"env_prefix": "APP_", "env_file": ".env"}

    @field_validator("llm_api_key")
    @classmethod
    def api_key_must_not_be_empty(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("APP_LLM_API_KEY is required")
        return v

    @field_validator("api_key")
    @classmethod
    def backend_api_key_must_not_be_empty(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("APP_API_KEY is required")
        return v


def create_settings(framework_settings: FrameworkSettings | None = None) -> Settings:
    """创建 backend Settings，可选使用 framework Settings 作为回退默认值。

    per D-01: ConfigLoader.load_settings() 提供默认值，env var 仍为最高优先级。
    pydantic-settings v2 解析顺序: init kwargs > env vars > env_file > defaults。
    因此只在 framework Settings 提供非默认值时才传 kwargs，让 env vars 优先。
    """
    if framework_settings is None:
        return Settings()

    # 只传递与默认值不同的 framework 值作为 kwargs。
    # 不传 kwargs 时 pydantic-settings 从 env vars / env_file / defaults 解析，
    # 确保 APP_LLM_API_KEY env var 优先于 framework 的空值。
    # 使用 Settings.model_fields 获取实际默认值，避免硬编码字符串耦合。
    kwargs: dict = {}
    defaults = Settings.model_fields

    if framework_settings.model != defaults["llm_model"].default:
        kwargs["llm_model"] = framework_settings.model

    if framework_settings.llm.provider != defaults["llm_provider"].default:
        kwargs["llm_provider"] = framework_settings.llm.provider

    fw_api_key = framework_settings.llm.api_key
    if fw_api_key.get_secret_value():
        kwargs["llm_api_key"] = fw_api_key

    if framework_settings.llm.base_url is not None:
        kwargs["llm_base_url"] = framework_settings.llm.base_url

    return Settings(**kwargs)
