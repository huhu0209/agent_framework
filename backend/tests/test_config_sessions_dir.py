from pathlib import Path

from app.config import Settings

# Settings 的 api_key / llm_api_key 字段有非空校验，与本任务无关；
# 这里给出 env 让 Settings() 可构造，聚焦验证 sessions_dir。
_REQUIRED_ENV = {"APP_API_KEY": "test-key", "APP_LLM_API_KEY": "test-key"}


def test_sessions_dir_default_points_home(monkeypatch):
    for k, v in _REQUIRED_ENV.items():
        monkeypatch.setenv(k, v)
    s = Settings()
    assert s.sessions_dir == Path.home() / ".agent-framework" / "sessions"


def test_sessions_dir_env_override(monkeypatch):
    for k, v in _REQUIRED_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("APP_SESSIONS_DIR", "/tmp/custom-sessions")
    s = Settings()
    assert s.sessions_dir == Path("/tmp/custom-sessions")
