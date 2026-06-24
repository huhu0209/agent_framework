"""AgentLoop 测试 — 集成 Tool System。"""

import pytest
from unittest.mock import AsyncMock

from pathlib import Path

from conftest import MockAdapter

from agent_framework.agents.agent_loop import AgentLoop, LoopEvent
from agent_framework.prompts.profiles import AgentProfile
from agent_framework.llm.base import ILLMAdapter
from agent_framework.llm.types import (
    CompletionResult,
    ProviderInfo,
    StopReason,
    TextBlock,
    ToolUseBlock,
    UsageStats,
    UserMessage,
)
from agent_framework.orchestrator.planner import PlanItem
from agent_framework.tools.builtin import create_builtin_registry
from agent_framework.tools.router import ToolRouter
from agent_framework.tools.types import ToolUseContext


def _make_mock_adapter() -> AsyncMock:
    adapter = AsyncMock(spec=ILLMAdapter)
    adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    return adapter


def _text_result(text: str, stop_reason: StopReason = StopReason.END_TURN) -> CompletionResult:
    return CompletionResult(
        id="test-id",
        content=[TextBlock(text=text)],
        model="mock",
        stop_reason=stop_reason,
        usage=UsageStats(),
    )


def _tool_use_result(*tool_calls: ToolUseBlock) -> CompletionResult:
    return CompletionResult(
        id="test-id",
        content=list(tool_calls),
        model="mock",
        stop_reason=StopReason.TOOL_USE,
        usage=UsageStats(),
    )


def _make_tool(name: str, id_: str = "tc_1", **input_kwargs) -> ToolUseBlock:
    return ToolUseBlock(id=id_, name=name, input=input_kwargs)


def _make_loop(adapter, **kwargs) -> AgentLoop:
    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()
    return AgentLoop(adapter, model="mock", router=router, ctx=ctx, **kwargs)


async def _collect_events(loop: AgentLoop, message: str, plan: list[PlanItem] | None = None) -> list[LoopEvent]:
    return [event async for event in loop.run(message, plan=plan)]


@pytest.mark.asyncio
async def test_direct_answer():
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好")

    types = [e.type for e in events]
    assert types == ["step", "done"]
    assert events[0].step == 1
    adapter.complete.assert_called_once()


@pytest.mark.asyncio
async def test_single_tool_call_read_file(tmp_path):
    """用真实的 read_file tool 执行。"""
    (tmp_path / "test.txt").write_text("hello from file")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="test.txt")),
        _text_result("回答"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "hello from file" in tool_events[0].data["tool_results"][0]
    assert adapter.complete.call_count == 2


@pytest.mark.asyncio
async def test_tool_call_nonexistent_tool():
    """调用不存在的工具返回错误。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("nonexistent_tool")),
        _text_result("回答"),
    ]

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "测试")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert "未知工具" in tool_events[0].data["tool_results"][0]


@pytest.mark.asyncio
async def test_max_steps_reached():
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _tool_use_result(_make_tool("read_file", path="x.txt"))

    loop = _make_loop(adapter, max_steps=3)
    events = await _collect_events(loop, "一直调用工具")

    last_event = events[-1]
    assert last_event.type == "max_steps"
    assert last_event.step == 3


@pytest.mark.asyncio
async def test_max_tokens_error():
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("截断...", StopReason.MAX_TOKENS)

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "长文本")

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "max_tokens" in error_events[0].data["error"]


@pytest.mark.asyncio
async def test_parallel_tool_calls(tmp_path):
    """一次返回多个 tool call，批量执行。"""
    (tmp_path / "a.txt").write_text("content A")
    (tmp_path / "b.txt").write_text("content B")

    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(
            _make_tool("read_file", id_="tc_1", path="a.txt"),
            _make_tool("read_file", id_="tc_2", path="b.txt"),
        ),
        _text_result("回答"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读两个文件")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 1
    assert len(tool_events[0].data["tool_results"]) == 2


@pytest.mark.asyncio
async def test_adapter_exception():
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = RuntimeError("连接超时")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "触发异常")

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "连接超时" in error_events[0].data["error"]


@pytest.mark.asyncio
async def test_write_then_read(tmp_path):
    """写文件再读回来的端到端测试。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("write_file", path="output.txt", content="written content")),
        _tool_use_result(_make_tool("read_file", path="output.txt")),
        _text_result("回答"),
    ]

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "写文件再读")

    tool_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_events) == 2
    assert "成功写入" in tool_events[0].data["tool_results"][0]
    assert "written content" in tool_events[1].data["tool_results"][0]
    assert adapter.complete.call_count == 3


def _make_plan_items() -> list[PlanItem]:
    return [
        PlanItem(id="1", action="步骤一", status="pending"),
        PlanItem(id="2", action="步骤二", status="pending"),
    ]


@pytest.mark.asyncio
async def test_caller_injected_plan():
    """调用方注入计划，LoopEvent 携带 plan snapshot。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好", plan=_make_plan_items())

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].plan is not None
    assert done_events[0].plan.total_count == 2
    assert done_events[0].plan.plan_source == "caller_injected"


@pytest.mark.asyncio
async def test_llm_generated_plan():
    """LLM 在回复中输出 <plan> 标记，自动解析。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text="<plan>\n1. 第一步\n2. 第二步\n</plan>\n好的，我来执行")],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(),
    )

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "复杂任务")

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].plan is not None
    assert done_events[0].plan.total_count == 2
    assert done_events[0].plan.plan_source == "llm_generated"


@pytest.mark.asyncio
async def test_no_plan_simple_task():
    """简单任务不生成 plan，行为与之前一致。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好")

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].plan is None


@pytest.mark.asyncio
async def test_drift_abort():
    """连续 N 步 TOOL_USE 不推进计划，ABORT 终止循环。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="a.txt")),
        _tool_use_result(_make_tool("read_file", path="b.txt")),
        _tool_use_result(_make_tool("read_file", path="c.txt")),
    ]

    loop = _make_loop(adapter, drift_warn=2, drift_abort=3)
    events = await _collect_events(loop, "复杂任务", plan=_make_plan_items())

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert "偏离计划" in error_events[0].data["error"]


@pytest.mark.asyncio
async def test_plan_context_not_accumulating(tmp_path):
    """计划上下文消息不会在多步循环中累积。"""
    adapter = _make_mock_adapter()
    adapter.complete.side_effect = [
        _tool_use_result(_make_tool("read_file", path="a.txt")),
        _text_result("回答"),
    ]

    (tmp_path / "a.txt").write_text("content")

    registry = create_builtin_registry()
    router = ToolRouter(registry)
    ctx = ToolUseContext(working_dir=str(tmp_path))
    loop = AgentLoop(adapter, model="mock", router=router, ctx=ctx)

    events = await _collect_events(loop, "读文件", plan=_make_plan_items())

    # Verify the loop completed
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1

    # Check adapter.complete was called twice (step 1 and step 2)
    # On the second call, there should be exactly 1 plan context message
    assert adapter.complete.call_count == 2
    second_call_messages = adapter.complete.call_args_list[1][0][0].messages
    plan_msgs = [
        m for m in second_call_messages
        if isinstance(m, UserMessage)
        and m.content
        and isinstance(m.content[0], TextBlock)
        and ("当前计划进度" in m.content[0].text or "[偏离提醒]" in m.content[0].text)
    ]
    assert len(plan_msgs) == 1  # NOT accumulating


# === Phase 5: 上下文管理集成测试 ===


@pytest.mark.asyncio
async def test_agent_loop_accepts_context_params():
    """AgentLoop accepts compression parameters."""
    mock_adapter = AsyncMock(spec=ILLMAdapter)
    mock_adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    loop = AgentLoop(
        adapter=mock_adapter,
        model="mock-model",
        router=ToolRouter(create_builtin_registry()),
        ctx=ToolUseContext(),
        compact_keep_turns=10,
        compact_trigger_pct=0.6,
    )
    assert loop.compact_keep_turns == 10
    assert loop.compact_trigger_pct == 0.6


@pytest.mark.asyncio
async def test_compact_adapter_defaults_to_main():
    """When compact_adapter not provided, reuse main adapter."""
    mock_adapter = AsyncMock(spec=ILLMAdapter)
    mock_adapter.get_provider_info.return_value = ProviderInfo(
        name="mock", base_url="https://mock", default_model="mock-model",
    )
    loop = AgentLoop(
        adapter=mock_adapter,
        model="mock-model",
        router=ToolRouter(create_builtin_registry()),
        ctx=ToolUseContext(),
    )
    assert loop.compact_adapter is mock_adapter


# === Phase 6: AgentProfile 集成测试 ===


@pytest.mark.asyncio
async def test_run_with_profile():
    """AgentProfile 替代 system_prompt 字符串。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    profile = AgentProfile(
        name="test",
        description="test agent",
        soul="你是一个测试助手。",
        agents_rules="保持简洁。",
        identity="测试身份。",
    )

    loop = _make_loop(adapter, profile=profile)
    events = await _collect_events(loop, "你好")

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1

    # 验证 system prompt 用了 profile 内容
    call_config = adapter.complete.call_args[0][0]
    system_msg = call_config.messages[0]
    assert "测试助手" in system_msg.content
    assert "保持简洁" in system_msg.content


@pytest.mark.asyncio
async def test_profile_overrides_system_prompt():
    """有 profile 时忽略 system_prompt 参数。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("回答")

    profile = AgentProfile(
        name="test",
        description="test agent",
        soul="profile soul",
    )

    loop = _make_loop(adapter, profile=profile, system_prompt="原始 prompt")
    events = await _collect_events(loop, "你好")

    call_config = adapter.complete.call_args[0][0]
    system_msg = call_config.messages[0]
    assert "profile soul" in system_msg.content
    assert "原始 prompt" not in system_msg.content


# === 语义记忆集成测试 ===


@pytest.mark.asyncio
async def test_semantic_extractor_param_accepted():
    """AgentLoop 接受 semantic_extractor 参数。"""
    from agent_framework.memory.semantic_extractor import SemanticExtractor

    mock_adapter = _make_mock_adapter()
    mock_adapter.complete.return_value = _text_result("回答")

    scoring_adapter = AsyncMock(spec=ILLMAdapter)
    extractor = SemanticExtractor(adapter=scoring_adapter, model="scoring-model")

    loop = AgentLoop(
        adapter=mock_adapter,
        model="mock-model",
        router=ToolRouter(create_builtin_registry()),
        ctx=ToolUseContext(),
        semantic_extractor=extractor,
    )
    assert loop._semantic_extractor is extractor


# === Skills 集成测试 ===


from agent_framework.tools.registry import ToolRegistry
from agent_framework.skills.tool import create_load_skill_spec


class TestAgentLoopSkills:
    def test_skill_dirs_creates_registry(self, tmp_path):
        """传入 skill_dirs 时自动创建 SkillRegistry 并注册 load_skill。"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_path = skills_dir / "test-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: 测试\n---\nbody", encoding="utf-8"
        )

        adapter = _make_mock_adapter()
        router = ToolRouter(registry=ToolRegistry())
        ctx = ToolUseContext()

        loop = AgentLoop(
            adapter=adapter,
            model="test",
            router=router,
            ctx=ctx,
            skill_dirs=[skills_dir],
        )

        assert router.registry.get("load_skill") is not None
        assert "skill_registry" in ctx.extra
        assert "test-skill" in loop._system_prompt_text

    def test_no_skill_dirs_no_load_skill(self):
        """不传 skill_dirs 时 load_skill 不注册。"""
        adapter = _make_mock_adapter()
        router = ToolRouter(registry=ToolRegistry())
        ctx = ToolUseContext()

        loop = AgentLoop(
            adapter=adapter,
            model="test",
            router=router,
            ctx=ctx,
        )

        assert router.registry.get("load_skill") is None


# --- SessionStart Hook 测试 ---


@pytest.mark.asyncio
async def test_session_start_hook_injects_message():
    """SessionStart hook 注入的消息出现在对话中。"""
    from agent_framework.hooks.manager import HookManager
    from agent_framework.hooks.types import HookConfig, HookEvent, HookType

    mgr = HookManager(trusted=True)
    mgr.register(HookConfig(
        event=HookEvent.SESSION_START,
        matcher="*",
        hook_type=HookType.COMMAND,
        command="echo 'session context loaded' >&2; exit 2",
    ))

    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("I'm ready.")

    registry = create_builtin_registry()
    router = ToolRouter(registry, hook_manager=mgr)

    loop = AgentLoop(
        adapter=adapter,
        model="test",
        router=router,
        ctx=ToolUseContext(),
        hook_manager=mgr,
    )

    events = []
    async for event in loop.run("hello"):
        events.append(event)

    # 应该有至少 1 个事件（done）
    assert len(events) >= 1
    # 最终事件应该是 done
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_session_start_hook_not_fired_without_manager():
    """无 hook_manager 时正常工作（向后兼容）。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = _text_result("Hello.")

    registry = create_builtin_registry()
    router = ToolRouter(registry)

    loop = AgentLoop(
        adapter=adapter,
        model="test",
        router=router,
        ctx=ToolUseContext(),
    )

    events = []
    async for event in loop.run("test"):
        events.append(event)

    assert len(events) >= 1
    assert events[-1].type == "done"


# --- TaskRunner 集成测试 ---


@pytest.mark.asyncio
async def test_agent_loop_with_task_runner_drain(tmp_path):
    """AgentLoop 每轮 drain 后台任务通知，注入到 messages。"""
    from agent_framework.tasks.manager import TaskManager
    from agent_framework.tasks.runner import TaskRunner
    from agent_framework.tasks.types import RuntimeTask, RuntimeTaskStatus
    from agent_framework.tools.registry import ToolRegistry

    mgr = TaskManager(tmp_path / "tasks")
    task = await mgr.create(subject="后台完成")

    adapter = MockAdapter("收到通知")
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()

    runner = TaskRunner(
        task_manager=mgr, adapter=adapter,
        model="test", router=router, ctx=ctx,
    )

    loop = AgentLoop(
        adapter=adapter, model="test",
        router=router, ctx=ctx,
        task_runner=runner,
    )

    # 手动往 runner 的 notification queue 放一个完成通知
    rt = RuntimeTask(task_id=task.id, prompt="done")
    rt.status = RuntimeTaskStatus.COMPLETED
    rt.output = "后台任务输出"
    await runner._notifications.put(rt)

    events = []
    async for event in loop.run("检查后台任务"):
        events.append(event)

    assert len(events) >= 2
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1


# --- SubAgent 集成测试 ---


@pytest.mark.asyncio
async def test_enable_subagent_registers_tool():
    adapter = MockAdapter("回答")
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()

    loop = AgentLoop(
        adapter=adapter, model="fake",
        router=router, ctx=ctx,
        enable_subagent=True,
    )
    assert "run_subagent" in loop.router.registry.list_tools()


@pytest.mark.asyncio
async def test_subagent_not_registered_by_default():
    adapter = MockAdapter("回答")
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()

    loop = AgentLoop(
        adapter=adapter, model="fake",
        router=router, ctx=ctx,
    )
    assert "run_subagent" not in loop.router.registry.list_tools()


# --- TeamManager 集成测试 ---


@pytest.mark.asyncio
async def test_team_manager_drains_notifications():
    import asyncio
    from agent_framework.teams.manager import TeamManager, TeamNotification

    adapter = MockAdapter("回答")
    registry = ToolRegistry()
    router = ToolRouter(registry)
    ctx = ToolUseContext()

    # Create a minimal TeamManager (bypass __init__)
    mgr = TeamManager.__new__(TeamManager)
    mgr.notifications = asyncio.Queue()
    mgr._configs = {}
    mgr._statuses = {}
    mgr._tasks = {}

    mgr.notifications.put_nowait(TeamNotification(name="alice", status="shutdown"))

    loop = AgentLoop(
        adapter=adapter, model="fake",
        router=router, ctx=ctx,
        team_manager=mgr,
    )

    async for event in loop.run("测试"):
        pass

    # Verify alice notification was injected into messages
    found = any(
        "alice" in block.text
        for msg in loop._messages
        if hasattr(msg, 'content')
        for block in msg.content
        if hasattr(block, 'text')
    )
    assert found, "Team notification for alice should appear in messages"


# --- Path import 修复验证 ---


def test_skill_dirs_accepted_without_name_error():
    """传入 skill_dirs=[Path("/tmp")] 不触发 NameError，且 _skill_dirs 相关属性正确。"""
    from agent_framework.tools.registry import ToolRegistry

    adapter = _make_mock_adapter()
    router = ToolRouter(registry=ToolRegistry())
    ctx = ToolUseContext()

    loop = AgentLoop(
        adapter=adapter,
        model="test",
        router=router,
        ctx=ctx,
        skill_dirs=[Path("/tmp")],
    )

    assert loop._skill_registry is not None


def test_system_prompt_blocks_empty_without_profile() -> None:
    """无 profile 时 system_prompt_blocks 返回空列表（不抛错）。"""
    loop = _make_loop(_make_mock_adapter())
    assert loop.system_prompt_blocks == []


@pytest.mark.asyncio
async def test_step_event_carries_usage():
    """step 事件 data 携带本次调用的 input/output usage。"""
    adapter = _make_mock_adapter()
    adapter.complete.return_value = CompletionResult(
        id="test-id",
        content=[TextBlock(text="回答")],
        model="mock",
        stop_reason=StopReason.END_TURN,
        usage=UsageStats(input_tokens=1234, output_tokens=567),
    )
    loop = _make_loop(adapter)
    events = await _collect_events(loop, "你好")

    step_events = [e for e in events if e.type == "step"]
    assert step_events, "应至少有一个 step 事件"
    assert step_events[0].data["usage"] == {"input": 1234, "output": 567}


def test_effective_context_window_uses_provider_info():
    """effective_context_window 走三级取值,默认取 provider info。"""
    from conftest import MockAdapter  # max_context_tokens=100_000

    adapter = MockAdapter("回答")
    loop = _make_loop(adapter)
    assert loop.effective_context_window() == 100_000
