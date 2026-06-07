"""Decomposer 测试 — LLM 驱动的任务分解。"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    UsageStats,
)
from agent_framework.orchestrator.decomposer import Decomposer
from agent_framework.orchestrator.models import SubTask, WorkerSpec
from agent_framework.orchestrator.worker_registry import WorkerRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_adapter_with_text(text: str) -> AsyncMock:
    """创建返回纯文本响应的 mock adapter。"""
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(input_tokens=100, output_tokens=50),
    )
    return adapter


def _make_registry(*specs: WorkerSpec) -> WorkerRegistry:
    """创建包含给定 WorkerSpec 的 registry。"""
    registry = WorkerRegistry()
    for spec in specs:
        registry.register(spec)
    return registry


def _dummy_factory():
    """一个无操作的 factory，仅供 WorkerSpec 使用。"""
    pass


# ---------------------------------------------------------------------------
# TestParseResponse — XML 解析（不涉及 LLM）
# ---------------------------------------------------------------------------

class TestParseResponse:
    """XML 解析测试。"""

    def test_single_subtask(self) -> None:
        """解析单个子任务。"""
        decomposer = Decomposer(_make_mock_adapter_with_text(""), model="mock")
        xml = (
            '<decomposition>\n'
            '<subtask id="1" worker="researcher" depends_on="">\n'
            '  搜索相关资料\n'
            '</subtask>\n'
            '</decomposition>'
        )
        result = decomposer._parse_response(xml)
        assert result is not None
        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].worker == "researcher"
        assert result[0].prompt == "搜索相关资料"
        assert result[0].depends_on == []

    def test_multiple_subtasks_with_deps(self) -> None:
        """解析多个带依赖的子任务。"""
        decomposer = Decomposer(_make_mock_adapter_with_text(""), model="mock")
        xml = (
            '<decomposition>\n'
            '<subtask id="1" worker="researcher" depends_on="">\n'
            '  搜索相关资料\n'
            '</subtask>\n'
            '<subtask id="2" worker="writer" depends_on="1">\n'
            '  根据资料撰写报告\n'
            '</subtask>\n'
            '</decomposition>'
        )
        result = decomposer._parse_response(xml)
        assert result is not None
        assert len(result) == 2
        assert result[1].depends_on == ["1"]

    def test_no_decomposition_tag_returns_none(self) -> None:
        """没有 decomposition 标签返回 None。"""
        decomposer = Decomposer(_make_mock_adapter_with_text(""), model="mock")
        result = decomposer._parse_response("这是普通的文本回复，没有 XML 标签")
        assert result is None

    def test_empty_decomposition_returns_none(self) -> None:
        """空的 decomposition 标签返回 None。"""
        decomposer = Decomposer(_make_mock_adapter_with_text(""), model="mock")
        result = decomposer._parse_response("<decomposition></decomposition>")
        assert result is None

    def test_multiple_comma_separated_deps(self) -> None:
        """逗号分隔的多依赖解析。"""
        decomposer = Decomposer(_make_mock_adapter_with_text(""), model="mock")
        xml = (
            '<decomposition>\n'
            '<subtask id="1" worker="researcher" depends_on="">\n'
            '  步骤一\n'
            '</subtask>\n'
            '<subtask id="2" worker="analyst" depends_on="">\n'
            '  步骤二\n'
            '</subtask>\n'
            '<subtask id="3" worker="writer" depends_on="1,2">\n'
            '  汇总\n'
            '</subtask>\n'
            '</decomposition>'
        )
        result = decomposer._parse_response(xml)
        assert result is not None
        assert result[2].depends_on == ["1", "2"]


# ---------------------------------------------------------------------------
# TestValidate — 验证逻辑
# ---------------------------------------------------------------------------

class TestValidate:
    """子任务验证测试。"""

    def test_valid_plan_passes(self) -> None:
        """合法计划通过验证。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索", factory=_dummy_factory),
            WorkerSpec(name="writer", description="写作", factory=_dummy_factory),
        )
        subtasks = [
            SubTask(id="1", worker="researcher", prompt="搜索", depends_on=[]),
            SubTask(id="2", worker="writer", prompt="写作", depends_on=["1"]),
        ]
        # Should not raise
        decomposer._validate(subtasks, registry)

    def test_unknown_worker_raises(self) -> None:
        """未知 worker 抛出 ValueError。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索", factory=_dummy_factory),
        )
        subtasks = [
            SubTask(id="1", worker="nonexistent", prompt="做事", depends_on=[]),
        ]
        with pytest.raises(ValueError, match="Worker not found"):
            decomposer._validate(subtasks, registry)

    def test_unknown_dep_raises(self) -> None:
        """未知依赖 id 抛出 ValueError。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索", factory=_dummy_factory),
        )
        subtasks = [
            SubTask(id="1", worker="researcher", prompt="搜索", depends_on=["99"]),
        ]
        with pytest.raises(ValueError, match="depends_on id"):
            decomposer._validate(subtasks, registry)

    def test_cycle_raises(self) -> None:
        """循环依赖抛出 ValueError，包含 cycle 或 循环。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="a", description="A", factory=_dummy_factory),
            WorkerSpec(name="b", description="B", factory=_dummy_factory),
        )
        subtasks = [
            SubTask(id="1", worker="a", prompt="A", depends_on=["2"]),
            SubTask(id="2", worker="b", prompt="B", depends_on=["1"]),
        ]
        with pytest.raises(ValueError, match="cycle|循环"):
            decomposer._validate(subtasks, registry)

    def test_deep_chain_no_recursion_error(self) -> None:
        """长依赖链不触发 RecursionError。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        specs = [
            WorkerSpec(name=f"w{i}", description=f"Worker {i}", factory=_dummy_factory)
            for i in range(200)
        ]
        registry = _make_registry(*specs)
        subtasks = [SubTask(id=str(i), worker=f"w{i}", prompt=f"Task {i}",
                            depends_on=[str(i-1)] if i > 0 else [])
                    for i in range(200)]
        # Should not raise RecursionError
        decomposer._validate(subtasks, registry)


# ---------------------------------------------------------------------------
# TestBuildPrompt — Prompt 构建
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    """Prompt 构建测试。"""

    def test_prompt_contains_worker_names(self) -> None:
        """Prompt 包含 worker 名称。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索资料", factory=_dummy_factory),
            WorkerSpec(name="writer", description="撰写文章", factory=_dummy_factory),
        )
        prompt = decomposer._build_prompt("帮我写一篇报告", registry)
        assert "researcher" in prompt
        assert "writer" in prompt

    def test_prompt_contains_format_instruction(self) -> None:
        """Prompt 包含输出格式指令。"""
        adapter = _make_mock_adapter_with_text("")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索", factory=_dummy_factory),
        )
        prompt = decomposer._build_prompt("任务", registry)
        assert "<decomposition>" in prompt


# ---------------------------------------------------------------------------
# TestDecompose — 端到端（mock adapter）
# ---------------------------------------------------------------------------

class TestDecompose:
    """端到端分解测试。"""

    @pytest.mark.asyncio
    async def test_success_returns_subtasks(self) -> None:
        """成功分解返回 SubTask 列表。"""
        xml = (
            '<decomposition>\n'
            '<subtask id="1" worker="researcher" depends_on="">\n'
            '  搜索 AI 最新进展\n'
            '</subtask>\n'
            '<subtask id="2" worker="writer" depends_on="1">\n'
            '  根据研究结果写报告\n'
            '</subtask>\n'
            '</decomposition>'
        )
        adapter = _make_mock_adapter_with_text(xml)
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索", factory=_dummy_factory),
            WorkerSpec(name="writer", description="写作", factory=_dummy_factory),
        )
        result = await decomposer.decompose("写一篇 AI 报告", registry)
        assert len(result) == 2
        assert result[0].worker == "researcher"
        assert result[1].depends_on == ["1"]

    @pytest.mark.asyncio
    async def test_unparseable_raises_value_error(self) -> None:
        """LLM 返回无法解析的内容时抛出 ValueError。"""
        adapter = _make_mock_adapter_with_text("我不理解你的问题")
        decomposer = Decomposer(adapter, model="mock")
        registry = _make_registry(
            WorkerSpec(name="researcher", description="搜索", factory=_dummy_factory),
        )
        with pytest.raises(ValueError, match="Failed to parse"):
            await decomposer.decompose("任务", registry)
