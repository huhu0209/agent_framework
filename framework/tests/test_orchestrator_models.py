"""Orchestrator data models 测试。"""
import pytest

from agent_framework.orchestrator.models import WorkerSpec


class TestWorkerSpec:
    def test_create_worker_spec(self):
        spec = WorkerSpec(name="data_agent", description="查询数据库中的设备数据", factory=lambda: None)
        assert spec.name == "data_agent"
        assert spec.description == "查询数据库中的设备数据"
        assert callable(spec.factory)

    def test_spec_is_frozen(self):
        spec = WorkerSpec(name="w", description="d", factory=lambda: None)
        with pytest.raises(AttributeError):
            spec.name = "modified"


class TestWorkerHandle:
    def test_create_running_handle(self):
        from agent_framework.orchestrator.models import WorkerHandle
        h = WorkerHandle(id="w_abc", worker_name="researcher", status="running")
        assert h.id == "w_abc"
        assert h.output == ""
        assert h.error is None

    def test_create_completed_handle(self):
        from agent_framework.orchestrator.models import WorkerHandle
        h = WorkerHandle(id="w_abc", worker_name="researcher", status="completed", output="result text")
        assert h.output == "result text"

    def test_create_failed_handle(self):
        from agent_framework.orchestrator.models import WorkerHandle
        h = WorkerHandle(id="w_abc", worker_name="researcher", status="failed", error="boom")
        assert h.error == "boom"

    def test_handle_is_frozen(self):
        from agent_framework.orchestrator.models import WorkerHandle
        h = WorkerHandle(id="w_abc", worker_name="researcher", status="running")
        with pytest.raises(AttributeError):
            h.status = "completed"
