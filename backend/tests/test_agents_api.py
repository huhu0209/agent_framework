"""Agent 管理 API 测试 — CRUD + /skills。"""
import pytest
from starlette.testclient import TestClient


@pytest.fixture
def agents_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_AGENTS_DIR", str(tmp_path))  # 隔离:agent 存临时目录
    from app.config import Settings
    from app.services.session import SessionManager
    from agent_framework.config.loader import ConfigLoader
    from main import app
    app.state.settings = Settings(agents_dir=tmp_path)
    app.state.session_manager = SessionManager()
    app.state.agent_factory = type("F", (), {"create_loop": lambda self, **kw: None})()
    app.state.config_loader = ConfigLoader(global_dir=tmp_path, project_dir=tmp_path)
    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_list_agents_empty(agents_client):
    res = agents_client.get("/api/v1/agents")
    assert res.status_code == 200
    assert res.json() == []


def test_create_then_get_and_list(agents_client):
    res = agents_client.post("/api/v1/agents", json={
        "name": "reviewer", "description": "审查员",
        "model": "m1", "skills": ["web-search"], "tools": ["read"],
        "soul": "你是审查员", "identity": "资深",
    })
    assert res.status_code == 201
    assert agents_client.get("/api/v1/agents").json() == [{"name": "reviewer", "description": "审查员"}]
    body = agents_client.get("/api/v1/agents/reviewer").json()
    assert body["name"] == "reviewer"
    assert body["soul"] == "你是审查员"
    assert body["skills"] == ["web-search"]


def test_create_duplicate_409(agents_client):
    agents_client.post("/api/v1/agents", json={"name": "a"})
    res = agents_client.post("/api/v1/agents", json={"name": "a"})
    assert res.status_code == 409


def test_create_invalid_name_400(agents_client):
    res = agents_client.post("/api/v1/agents", json={"name": "../evil"})
    assert res.status_code == 400


def test_update_overwrites(agents_client):
    agents_client.post("/api/v1/agents", json={"name": "a", "description": "old"})
    res = agents_client.put("/api/v1/agents/a", json={"name": "a", "description": "new", "soul": "new soul"})
    assert res.status_code == 200
    body = agents_client.get("/api/v1/agents/a").json()
    assert body["description"] == "new"
    assert body["soul"] == "new soul"


def test_delete_removes(agents_client):
    agents_client.post("/api/v1/agents", json={"name": "a"})
    res = agents_client.delete("/api/v1/agents/a")
    assert res.status_code == 204
    assert agents_client.get("/api/v1/agents/a").status_code == 404


def test_get_missing_404(agents_client):
    assert agents_client.get("/api/v1/agents/nope").status_code == 404


def test_skills_returns_list(agents_client):
    res = agents_client.get("/api/v1/skills")
    assert res.status_code == 200
    assert isinstance(res.json(), list)  # 临时 dir 无 skill → []
