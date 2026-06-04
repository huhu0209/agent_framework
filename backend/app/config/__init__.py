"""应用配置 — 从环境变量 / .env 读取。"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_base_url: str | None = None

    model_config = {"env_prefix": "APP_", "env_file": ".env"}

    @field_validator("llm_api_key")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("APP_LLM_API_KEY is required")
        return v
