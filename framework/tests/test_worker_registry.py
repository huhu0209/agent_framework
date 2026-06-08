import pytest

from agent_framework.orchestrator.models import WorkerSpec
from agent_framework.orchestrator.worker_registry import WorkerRegistry


def _make_spec(name: str, desc: str = "测试 Worker") -> WorkerSpec:
    return WorkerSpec(name=name, description=desc, factory=lambda: None)


class TestRegisterAndGet:
    def test_register_and_get(self):
        registry = WorkerRegistry()
        spec = _make_spec("data_agent", "查询数据库")
        registry.register(spec)
        assert registry.get("data_agent") is spec

    def test_get_unknown_raises_key_error(self):
        registry = WorkerRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")


class TestHasWorkers:
    def test_empty_registry(self):
        assert WorkerRegistry().has_workers() is False

    def test_with_workers(self):
        registry = WorkerRegistry()
        registry.register(_make_spec("data_agent"))
        assert registry.has_workers() is True


class TestDescribeForLLM:
    def test_describe_empty(self):
        assert "无" in WorkerRegistry().describe_for_llm()

    def test_describe_with_workers(self):
        registry = WorkerRegistry()
        registry.register(_make_spec("data_agent", "查询数据库中的设备数据"))
        registry.register(_make_spec("rag_agent", "检索维修手册和知识库"))
        desc = registry.describe_for_llm()
        assert "data_agent" in desc
        assert "查询数据库中的设备数据" in desc
        assert "rag_agent" in desc
        assert "检索维修手册和知识库" in desc


class TestRegisterValidation:
    def test_empty_name_raises(self):
        registry = WorkerRegistry()
        with pytest.raises(ValueError, match="cannot be empty"):
            registry.register(_make_spec("", "desc"))

    def test_invalid_name_raises(self):
        registry = WorkerRegistry()
        with pytest.raises(ValueError, match="Invalid worker name"):
            registry.register(_make_spec("123bad", "desc"))

    def test_duplicate_name_raises(self):
        registry = WorkerRegistry()
        registry.register(_make_spec("data_agent"))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_make_spec("data_agent"))
