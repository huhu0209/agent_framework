"""Orchestrator data models 测试。"""
from agent_framework.orchestrator.models import SubTask, SubTaskResult, WorkerSpec


class TestWorkerSpec:
    def test_create_worker_spec(self):
        spec = WorkerSpec(name="data_agent", description="查询数据库中的设备数据", factory=lambda: None)
        assert spec.name == "data_agent"
        assert spec.description == "查询数据库中的设备数据"
        assert callable(spec.factory)


class TestSubTask:
    def test_create_subtask_no_deps(self):
        task = SubTask(id="1", worker="data_agent", prompt="查询报警记录", depends_on=[])
        assert task.id == "1"
        assert task.worker == "data_agent"
        assert task.prompt == "查询报警记录"
        assert task.depends_on == []

    def test_create_subtask_with_deps(self):
        task = SubTask(id="2", worker="history_agent", prompt="搜索历史案例", depends_on=["1"])
        assert task.depends_on == ["1"]


class TestSubTaskResult:
    def test_success_result(self):
        result = SubTaskResult(id="1", worker="data_agent", output="报警记录3条", success=True, error=None)
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        result = SubTaskResult(id="1", worker="data_agent", output="", success=False, error="LLM API timeout")
        assert result.success is False
        assert result.error == "LLM API timeout"
