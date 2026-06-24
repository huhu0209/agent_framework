import pytest
from starlette.testclient import TestClient


@pytest.fixture
def fs_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:5173")
    from app.config import Settings
    from app.services.session import SessionManager
    from main import app
    app.state.settings = Settings()
    app.state.session_manager = SessionManager()
    app.state.agent_factory = type("F", (), {"create_loop": lambda self, working_dir=None: None})()
    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_list_dirs_returns_only_subdirs(fs_client, tmp_path):
    (tmp_path / "subA").mkdir()
    (tmp_path / "subB").mkdir()
    (tmp_path / "file.txt").write_text("x")
    res = fs_client.get("/api/v1/fs/list", params={"path": str(tmp_path)})
    assert res.status_code == 200
    names = [d["name"] for d in res.json()]
    assert "subA" in names and "subB" in names
    assert "file.txt" not in names


def test_list_dirs_filters_hidden(fs_client, tmp_path):
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "visible").mkdir()
    res = fs_client.get("/api/v1/fs/list", params={"path": str(tmp_path)})
    names = [d["name"] for d in res.json()]
    assert "visible" in names and ".hidden" not in names


def test_list_dirs_missing_path_400(fs_client):
    res = fs_client.get("/api/v1/fs/list", params={"path": "/no/such/path/xyz"})
    assert res.status_code == 400


def test_list_dirs_requires_auth(tmp_path):
    # 无 X-API-Key → 401
    monkeypatch_local = pytest.MonkeyPatch()
    monkeypatch_local.setenv("APP_LLM_API_KEY", "test-key")
    monkeypatch_local.setenv("APP_API_KEY", "test-key")
    monkeypatch_local.setenv("APP_CORS_ORIGINS", "http://localhost:5173")
    from app.config import Settings
    from app.services.session import SessionManager
    from main import app
    app.state.settings = Settings()
    app.state.session_manager = SessionManager()
    app.state.agent_factory = type("F", (), {"create_loop": lambda self, working_dir=None: None})()
    c = TestClient(app)  # no X-API-Key header
    res = c.get("/api/v1/fs/list", params={"path": str(tmp_path)})
    assert res.status_code == 401
    monkeypatch_local.undo()
