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


def test_write_agent_is_atomic_no_tmp_residue(agents_client):
    """_write_agent 后目标目录完整(5 文件),无临时目录残留。

    原子写:先写 .<name>.xxx 临时目录,全部成功后替换目标。
    中途崩溃应回滚(删临时目录),不留不一致状态。
    """
    agents_client.post("/api/v1/agents", json={
        "name": "atomic", "description": "d", "soul": "soul-content", "identity": "id",
    })
    agents_root = agents_client.app.state.settings.agents_dir
    agent_dir = agents_root / "atomic"
    # 5 个文件都在
    assert (agent_dir / "agent.json").exists()
    for f in ["soul.md", "identity.md", "agents.md", "tool_guidance.md"]:
        assert (agent_dir / f).exists()
    # 无临时目录残留(.atomic.xxx)
    residues = [p for p in agents_root.iterdir() if p.name.startswith(".atomic")]
    assert residues == []


def test_update_agent_atomic_overwrites(agents_client):
    """PUT 更新后,新内容完整写入,旧内容被替换(原子替换不留混合状态)。"""
    agents_client.post("/api/v1/agents", json={"name": "a", "soul": "old-soul"})
    res = agents_client.put(
        "/api/v1/agents/a", json={"name": "a", "soul": "new-soul", "identity": "new-id"},
    )
    assert res.status_code == 200
    body = agents_client.get("/api/v1/agents/a").json()
    assert body["soul"] == "new-soul"
    assert body["identity"] == "new-id"
    # 无临时目录残留
    agents_root = agents_client.app.state.settings.agents_dir
    residues = [p for p in agents_root.iterdir() if p.name.startswith(".a.")]
    assert residues == []


def test_write_agent_failure_rolls_back_no_corruption(agents_client, monkeypatch):
    """中途写失败时,临时目录回滚,既有 agent 目录保持原样(不被损坏)。

    场景:PUT 更新已有 agent 时,写到一半崩溃(模拟 disk error)。
    非原子实现此时已部分覆盖目标文件 → 数据损坏;
    原子实现回滚临时目录,目标目录完整保留旧内容。
    """
    # 先建一个完整的 agent
    agents_client.post("/api/v1/agents", json={
        "name": "victim", "soul": "original-soul", "identity": "original-id",
    })

    # 注入故障:让 Path.write_text 写 soul.md 时抛异常(模拟中途崩溃)
    from app.api.v1 import agents as agents_module
    original_write_text = agents_module.Path.write_text

    call_count = {"n": 0}

    def flaky_write_text(self, data, *args, **kwargs):
        call_count["n"] += 1
        # 在写 persona 文件(第 2 次起,soul.md)时崩溃
        if call_count["n"] >= 2:
            raise OSError("simulated disk failure mid-write")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(agents_module.Path, "write_text", flaky_write_text)

    # PUT 更新 — 应因注入的故障失败。
    # TestClient 默认 raise_server_exceptions=True 会把服务端异常抛给测试;
    # 用 raise_server_exceptions=False 让它返回 500 响应(模拟生产边界)。
    app = agents_client.app
    with TestClient(app, headers={"X-API-Key": "test-key"}, raise_server_exceptions=False) as client:
        res = client.put("/api/v1/agents/victim", json={
            "name": "victim", "soul": "corrupted-attempt",
        })
    assert res.status_code == 500  # 故障导致 500(非原子实现会留下损坏的半成品)

    # 关键:原 agent 目录必须完整保留(原子回滚)
    body = agents_client.get("/api/v1/agents/victim").json()
    assert body["soul"] == "original-soul"  # 旧内容未被破坏
    assert body["identity"] == "original-id"
    # 无临时目录残留
    agents_root = agents_client.app.state.settings.agents_dir
    residues = [p for p in agents_root.iterdir() if p.name.startswith(".victim.")]
    assert residues == []
