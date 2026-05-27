"""SubAgent 测试 — filtered router + run_subagent + spec 创建。"""

import pytest

from agent_framework.agents.agent_loop import AgentLoop
from agent_framework.agents.sub_agent import (
    RECURSIVE_TOOLS,
    create_filtered_router,
    create_run_subagent_spec,
    run_subagent,
)
from agent_framework.llm.types import (
    CompletionConfig,
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    ToolUseBlock,
    UsageStats,
)
from agent_framework.tools.registry import ToolRegistry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolResult, ToolSpec, ToolUseContext


# --- Fake Adapters ---


class FakeAdapter:
    """返回预设文本的最小 adapter。"""

    def __init__(self, text: str = "子代理完成了任务") -> None:
        self._text = text

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        return CompletionResult(
            id="fake",
            model=config.model,
            content=[TextBlock(text=self._text)],
            stop_reason=StopReason.END_TURN,
            usage=UsageStats(input_tokens=10, output_tokens=5),
        )

    def get_provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="fake",
            base_url="https://fake",
            default_model="fake-model",
            max_context_tokens=128000,
        )


class ErrorAdapter:
    """complete() 抛出异常的 adapter。"""

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        raise RuntimeError("模型连接失败")

    def get_provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="error",
            base_url="https://error",
            default_model="error-model",
            max_context_tokens=128000,
        )


class NeverEndAdapter:
    """始终返回 TOOL_USE 的 adapter — 模拟无限循环。"""

    def __init__(self) -> None:
        self._call_count = 0

    async def complete(self, config: CompletionConfig) -> CompletionResult:
        self._call_count += 1
        return CompletionResult(
            id=f"never-end-{self._call_count}",
            model=config.model,
            content=[
                ToolUseBlock(
                    id=f"tu_{self._call_count}",
                    name="nonexistent_tool",
                    input={},
                )
            ],
            stop_reason=StopReason.TOOL_USE,
            usage=UsageStats(input_tokens=10, output_tokens=5),
        )

    def get_provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="never-end",
            base_url="https://never-end",
            default_model="never-end-model",
            max_context_tokens=128000,
        )


# --- Helpers ---


def _make_spec(name: str) -> ToolSpec:
    """创建一个最小 ToolSpec，handler 返回空结果。"""

    async def _handler(args: dict, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(content=f"{name} executed")

    return ToolSpec(
        name=name,
        description=f"Test tool {name}",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_handler,
    )


def _make_router(*names: str) -> ToolRouter:
    registry = ToolRegistry()
    for name in names:
        registry.register(_make_spec(name))
    return ToolRouter(registry=registry)


# --- Tests ---


def test_filtered_router_excludes_recursive_tools():
    """RECURSIVE_TOOLS 被自动排除。"""
    router = _make_router("run_subagent", "task_create", "spawn_teammate", "safe_tool")
    filtered = create_filtered_router(router, allowed=None)

    tool_names = filtered.registry.list_tools()
    assert "safe_tool" in tool_names
    for recursive in RECURSIVE_TOOLS:
        assert recursive not in tool_names


def test_filtered_router_with_allowed_list():
    """指定 allowed_tools 时只保留指定工具（排除递归工具）。"""
    router = _make_router("read_file", "write_file", "run_subagent")
    filtered = create_filtered_router(router, allowed=["read_file", "run_subagent"])

    tool_names = filtered.registry.list_tools()
    assert tool_names == ["read_file"]


@pytest.mark.asyncio
async def test_run_subagent_returns_summary():
    """正常完成时返回子代理的文本输出。"""
    adapter = FakeAdapter(text="子代理分析完成：发现3个问题")
    router = _make_router("safe_tool")
    ctx = ToolUseContext()

    result = await run_subagent(
        prompt="分析代码",
        parent_router=router,
        adapter=adapter,
        model="fake-model",
        ctx=ctx,
    )

    assert result == "子代理分析完成：发现3个问题"


@pytest.mark.asyncio
async def test_run_subagent_error_returns_prefix():
    """adapter 抛异常时返回带 [子代理错误] 前缀的消息。"""
    adapter = ErrorAdapter()
    router = _make_router("safe_tool")
    ctx = ToolUseContext()

    result = await run_subagent(
        prompt="触发错误",
        parent_router=router,
        adapter=adapter,
        model="error-model",
        ctx=ctx,
    )

    assert result.startswith("[子代理错误]")
    assert "模型连接失败" in result


@pytest.mark.asyncio
async def test_run_subagent_max_steps_returns_partial():
    """达到最大步数时返回部分结果 + 限制提示。"""
    adapter = NeverEndAdapter()
    router = _make_router("safe_tool")
    ctx = ToolUseContext()

    result = await run_subagent(
        prompt="无限循环",
        parent_router=router,
        adapter=adapter,
        model="never-end-model",
        ctx=ctx,
        max_steps=2,
    )

    assert "[子代理达到最大步数限制]" in result


@pytest.mark.asyncio
async def test_create_run_subagent_spec_handler():
    """create_run_subagent_spec 返回的 ToolSpec handler 可正常调用。"""
    adapter = FakeAdapter(text="子任务完成")
    router = _make_router("safe_tool")
    ctx = ToolUseContext()

    spec = create_run_subagent_spec(
        adapter=adapter,
        model="fake-model",
        router=router,
        ctx=ctx,
    )

    assert spec.name == "run_subagent"
    assert spec.timeout_ms == 120_000
    assert "prompt" in spec.parameters.required

    result = await spec.handler({"prompt": "做点什么"}, ctx)
    assert isinstance(result, ToolResult)
    assert result.content == "子任务完成"
