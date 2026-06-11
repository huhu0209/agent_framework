"""Settings 模型 + ENV_VAR_MAP + apply_env_vars 测试。"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from agent_framework.config.settings import (
    ENV_VAR_MAP,
    LlmConfig,
    LoggingConfig,
    PermissionsConfig,
    ServerConfig,
    Settings,
    apply_env_vars,
)


class TestSettingsDefaults:
    """Settings 全默认值实例化测试。"""

    def test_default_settings_instantiation(self) -> None:
        """Settings() 无参数实例化成功，所有字段有默认值。"""
        s = Settings()
        assert s.model == "claude-sonnet-4-20250514"
        assert isinstance(s.llm, LlmConfig)
        assert isinstance(s.server, ServerConfig)
        assert isinstance(s.logging, LoggingConfig)
        assert isinstance(s.permissions, PermissionsConfig)

    def test_default_llm_config(self) -> None:
        s = Settings()
        assert s.llm.provider == "anthropic"
        assert s.llm.api_key.get_secret_value() == ""
        assert s.llm.base_url is None

    def test_default_server_config(self) -> None:
        s = Settings()
        assert s.server.host == "0.0.0.0"
        assert s.server.port == 30002
        assert s.server.cors_origins == ["http://localhost:30001"]

    def test_default_logging_config(self) -> None:
        s = Settings()
        assert s.logging.level == "info"

    def test_default_permissions_config(self) -> None:
        s = Settings()
        assert s.permissions.allow == []
        assert s.permissions.deny == []
        assert s.permissions.ask == []


class TestSettingsFromDict:
    """Settings.model_validate 从 dict 构造和部分覆盖。"""

    def test_partial_override_model(self) -> None:
        """部分覆盖 model，其余字段保持默认。"""
        s = Settings.model_validate({"model": "gpt-4"})
        assert s.model == "gpt-4"
        assert s.llm.provider == "anthropic"

    def test_nested_llm_config(self) -> None:
        """嵌套 LlmConfig 从 dict 构造。"""
        s = Settings.model_validate(
            {"llm": {"provider": "openai", "api_key": "sk-test"}}
        )
        assert s.llm.provider == "openai"
        assert isinstance(s.llm.api_key, SecretStr)
        assert s.llm.api_key.get_secret_value() == "sk-test"
        assert s.model == "claude-sonnet-4-20250514"

    def test_full_override(self) -> None:
        """完整覆盖所有字段。"""
        s = Settings.model_validate(
            {
                "model": "gpt-4",
                "llm": {"provider": "openai", "api_key": "sk-test", "base_url": "https://api.openai.com"},
                "server": {"host": "127.0.0.1", "port": 8080, "cors_origins": ["*"]},
                "logging": {"level": "debug"},
                "permissions": {"allow": ["Bash(*)"], "deny": [], "ask": []},
            }
        )
        assert s.model == "gpt-4"
        assert s.llm.provider == "openai"
        assert s.server.port == 8080
        assert s.logging.level == "debug"
        assert s.permissions.allow == ["Bash(*)"]


class TestSecretStrBehavior:
    """SecretStr 序列化行为测试。"""

    def test_model_dump_json_masks_api_key(self) -> None:
        """model_dump(mode='json') 返回 api_key 为掩码字符串（SecretStr 安全行为）。"""
        s = Settings.model_validate({"llm": {"api_key": "sk-secret"}})
        dumped = s.model_dump(mode="json")
        assert dumped["llm"]["api_key"] == "**********"

    def test_model_dump_preserves_secret_str(self) -> None:
        """model_dump() 返回 api_key 为 SecretStr 对象。"""
        s = Settings.model_validate({"llm": {"api_key": "sk-secret"}})
        dumped = s.model_dump()
        assert isinstance(dumped["llm"]["api_key"], SecretStr)


class TestEnvVarMap:
    """ENV_VAR_MAP 映射完整性测试。"""

    def test_map_contains_all_scalar_fields(self) -> None:
        """ENV_VAR_MAP 包含所有标量字段映射。"""
        expected_keys = {
            "APP_MODEL",
            "APP_LLM__PROVIDER",
            "APP_LLM__API_KEY",
            "APP_LLM__BASE_URL",
            "APP_SERVER__HOST",
            "APP_SERVER__PORT",
            "APP_LOGGING__LEVEL",
        }
        assert set(ENV_VAR_MAP.keys()) == expected_keys

    def test_map_paths_are_correct(self) -> None:
        """ENV_VAR_MAP 路径值正确。"""
        assert ENV_VAR_MAP["APP_MODEL"] == "model"
        assert ENV_VAR_MAP["APP_LLM__PROVIDER"] == "llm.provider"
        assert ENV_VAR_MAP["APP_LLM__API_KEY"] == "llm.api_key"
        assert ENV_VAR_MAP["APP_LLM__BASE_URL"] == "llm.base_url"
        assert ENV_VAR_MAP["APP_SERVER__HOST"] == "server.host"
        assert ENV_VAR_MAP["APP_SERVER__PORT"] == "server.port"
        assert ENV_VAR_MAP["APP_LOGGING__LEVEL"] == "logging.level"


class TestApplyEnvVars:
    """apply_env_vars 环境变量注入测试。"""

    def test_override_existing_scalar(self) -> None:
        """环境变量覆盖已有标量值。"""
        result = apply_env_vars({"model": "a"}, {"APP_MODEL": "b"})
        assert result == {"model": "b"}

    def test_inject_nested_path(self) -> None:
        """嵌套路径注入。"""
        result = apply_env_vars(
            {"model": "a"}, {"APP_LLM__PROVIDER": "openai"}
        )
        assert result == {"model": "a", "llm": {"provider": "openai"}}

    def test_ignore_unmapped_vars(self) -> None:
        """忽略未映射的环境变量。"""
        result = apply_env_vars({"model": "a"}, {"UNKNOWN_VAR": "x"})
        assert result == {"model": "a"}

    def test_does_not_modify_input(self) -> None:
        """不修改输入 dict（不可变性）。"""
        original = {"model": "a", "llm": {"provider": "anthropic"}}
        env = {"APP_MODEL": "gpt-4"}
        result = apply_env_vars(original, env)
        assert original == {"model": "a", "llm": {"provider": "anthropic"}}
        assert result["model"] == "gpt-4"

    def test_multiple_env_vars(self) -> None:
        """多个环境变量同时注入。"""
        result = apply_env_vars(
            {"model": "a"},
            {"APP_MODEL": "b", "APP_LOGGING__LEVEL": "debug"},
        )
        assert result == {"model": "b", "logging": {"level": "debug"}}

    def test_deeply_nested_override(self) -> None:
        """覆盖已有的嵌套值。"""
        original = {"llm": {"provider": "anthropic", "api_key": "old"}}
        result = apply_env_vars(original, {"APP_LLM__PROVIDER": "openai"})
        assert result["llm"]["provider"] == "openai"
        assert result["llm"]["api_key"] == "old"


class TestLeafDependency:
    """config/ 叶依赖约束测试。"""

    def test_config_does_not_import_framework_modules(self) -> None:
        """config/ 模块不导入 agent_framework 其他模块。"""
        import ast
        import pathlib

        config_dir = pathlib.Path(__file__).resolve().parent.parent / "agent_framework" / "config"
        forbidden_prefixes = ("agent_framework.",)
        allowed_imports = ("agent_framework.config",)

        for py_file in config_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if any(node.module.startswith(p) for p in forbidden_prefixes):
                        if not any(node.module.startswith(a) for a in allowed_imports):
                            pytest.fail(
                                f"{py_file.name} imports '{node.module}' — "
                                f"config/ must not import other framework modules"
                            )

    def test_barrel_exports_all_symbols(self) -> None:
        """barrel __init__.py 导出所有公共符号。"""
        from agent_framework.config import __all__

        expected = {
            "ENV_VAR_MAP",
            "LlmConfig",
            "LoggingConfig",
            "PermissionsConfig",
            "ServerConfig",
            "Settings",
            "apply_env_vars",
            "ConfigLoader",
            "merge_settings",
        }
        assert set(__all__) == expected
