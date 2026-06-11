"""全局运行时配置 — Settings Pydantic 模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, SecretStr


class LlmConfig(BaseModel):
    """LLM 连接配置。"""

    provider: str = "anthropic"
    api_key: SecretStr = SecretStr("")
    base_url: str | None = None


class ServerConfig(BaseModel):
    """服务端配置。"""

    host: str = "0.0.0.0"
    port: int = 30002
    cors_origins: list[str] = ["http://localhost:30001"]


class LoggingConfig(BaseModel):
    """日志配置。"""

    level: str = "info"


class PermissionsConfig(BaseModel):
    """权限配置。"""

    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []


class Settings(BaseModel):
    """全局运行时配置 — 统一 schema。

    字段与 settings.json 结构直接对应。merge_settings() 合并后
    的 dict 通过 Settings.model_validate(merged) 创建实例。
    环境变量覆盖由 Phase 21 的 ConfigLoader 在合并后注入。
    """

    model: str = "claude-sonnet-4-20250514"
    llm: LlmConfig = LlmConfig()
    server: ServerConfig = ServerConfig()
    logging: LoggingConfig = LoggingConfig()
    permissions: PermissionsConfig = PermissionsConfig()


# 环境变量名 -> Settings 字段路径（点分隔），仅标量字段
ENV_VAR_MAP: dict[str, str] = {
    "APP_MODEL": "model",
    "APP_LLM__PROVIDER": "llm.provider",
    "APP_LLM__API_KEY": "llm.api_key",
    "APP_LLM__BASE_URL": "llm.base_url",
    "APP_SERVER__HOST": "server.host",
    "APP_SERVER__PORT": "server.port",
    "APP_LOGGING__LEVEL": "logging.level",
}


def apply_env_vars(merged: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """将环境变量注入到合并后 dict 中的标量字段。

    仅处理 ENV_VAR_MAP 中预定义的键，忽略未知环境变量。
    不修改输入 dict，返回新 dict。

    Args:
        merged: 合并后的配置 dict。
        env: 环境变量 dict（通常是 os.environ 的子集）。

    Returns:
        注入环境变量后的新 dict。
    """
    import copy

    result: dict[str, Any] = copy.deepcopy(merged)

    for env_key, field_path in ENV_VAR_MAP.items():
        if env_key not in env:
            continue

        parts = field_path.split(".")
        current: dict[str, Any] = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = env[env_key]

    return result
