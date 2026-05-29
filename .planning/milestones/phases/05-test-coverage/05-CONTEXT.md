# Phase 5: 测试覆盖补充 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

补充框架层（`framework/agent_framework/`）关键路径测试，覆盖 HIGH 优先级测试缺口，确保所有新测试通过且无回归。

**覆盖缺口（3 个）：**
1. TeamManager loop 行为测试 — `_loop` 的 shutdown、idle 超时、status 转换、notification queue
2. 安全边界 × 工具执行集成测试 — AgentLoop → ToolRouter → safe_path 全链路
3. PermissionPipeline 边界情况 — _CRITICAL_TOOLS、allowed+disallowed 冲突、无注解决策边界

**产出：** 新增测试全部通过，全量 675+ 测试无回归

**不包含：**
- 新功能开发
- 已有单元测试的重复覆盖（safe_path 单元测试、file_tools 单元测试）
- 代码覆盖率工具引入（无 pytest-cov 配置，不在此 phase 添加）

</domain>

<decisions>
## Implementation Decisions

### TeamManager loop 深度测试
- **D-01:** 使用 monkeypatch 替换 `asyncio.sleep`，让测试瞬间通过 idle 轮询循环。不依赖真实时间等待
- **D-02:** mock AgentLoop — 用 `unittest.mock.AsyncMock` 替代真实 AgentLoop，使 `loop.run()` 返回预设事件序列。仅验证 _loop 内部行为逻辑（status 转换、shutdown 响应），不测 AgentLoop.run 的执行结果
- **D-03:** 测试追加到 `framework/tests/test_teams_manager.py`，用 `TestTeamLoop` class 分组
- **D-04:** 按行为拆分多个独立测试：shutdown_via_inbox、idle_timeout_shutdown、status_transitions（IDLE→WORKING→IDLE）、notification_emitted、inbox_processing。每个测试验证单一行为，失败时容易定位

### 安全边界 × 工具执行集成测试
- **D-05:** 集成深度为 AgentLoop 全链路 — 创建真实 AgentLoop + 真实 ToolRouter（create_builtin_registry）+ FakeAdapter，让 loop 通过 tool_use 调用 read_file("../../../etc/passwd")，验证最终返回 error 事件
- **D-06:** 新建 `framework/tests/test_safety_integration.py`，专门放安全集成测试
- **D-07:** 仅覆盖核心场景：2-3 个测试（路径遍历被拒、绝对路径被拒、正常文件访问仍可用）。边界细节已有单元测试覆盖，集成测试只验证链路通畅

### PermissionPipeline 边界情况
- **D-08:** 仅测试 pipeline 单元级边界，不涉及 ToolRouter 集成
- **D-09:** 追加到 `framework/tests/test_permissions.py`，用 `TestEdgeCases` class 分组
- **D-10:** 4 个核心边界测试：(1) disallowed 优先于 allowed、(2) 无注解 + ask → LOW ASK、(3) _CRITICAL_TOOLS 为空时不影响正常决策、(4) destructive+idempotent → MEDIUM ASK

### 测试组织
- **D-11:** 所有测试遵循现有模式：中文 docstring、`tmp_path` 做文件系统、`AsyncMock(spec=ILLMAdapter)` 做 LLM mock、`assert` 语句
- **D-12:** 最后一个 plan 运行全量测试确认无回归（`cd framework && pytest tests/ -v`）

### Claude's Discretion
- monkeypatch 的具体实现方式（patch `asyncio.sleep` 的范围）
- FakeAdapter vs MockAdapter 的选择
- 具体测试函数命名
- AgentLoop mock 的 setup 方式（side_effect 序列 vs return_value）
- 集成测试中 FakeAdapter 的 complete 返回值设计

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 测试规范
- `.planning/codebase/TESTING.md` — 测试框架配置、mock 模式、fixture 约定、新增测试步骤
- `.planning/codebase/CONVENTIONS.md` — 编码规范（命名、import、类型注解）

### 测试缺口来源
- `.planning/ROADMAP.md` §Phase 5 — 4 个任务和验证标准
- `.planning/REQUIREMENTS.md` §R5: 测试覆盖审查 — 已知缺口列表和验收标准
- `.planning/codebase/CONCERNS.md` §Test Gaps — 测试覆盖缺口的详细分析

### 核心源文件（测试目标）
- `framework/agent_framework/teams/manager.py:66-115` — `_loop` 方法（shutdown inbox、idle 超时、status 转换、notification）
- `framework/agent_framework/teams/bus.py` — MessageBus（read_inbox、send）
- `framework/agent_framework/safety/boundary.py:17-25` — `safe_path()` 函数
- `framework/agent_framework/safety/permissions.py:54-110` — PermissionPipeline.check + _annotate_decision
- `framework/agent_framework/tools/builtin/file_tools.py:16-48` — read_file / write_file（safe_path 集成点）
- `framework/agent_framework/tools/router.py:58-156` — ToolRouter.dispatch

### 现有测试文件（追加目标）
- `framework/tests/test_teams_manager.py` — 4 个现有测试，loop 测试追加
- `framework/tests/test_permissions.py` — 10 个现有测试，边界测试追加
- `framework/tests/conftest.py` — MockAdapter、memory_dir fixture

### 已有报告（格式参考）
- `docs/reviews/SECURITY-REVIEW.md` — Phase 2 安全审查报告
- `docs/reviews/PERF-REVIEW.md` — Phase 4 性能审查报告

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/tests/test_agent_loop.py` 中的 `_make_mock_adapter()`、`_collect_events()` — 集成测试可直接复用
- `framework/tests/test_teams_manager.py` 中的 `FakeAdapter` 和 `team_mgr` fixture — loop 测试可复用
- `framework/tests/conftest.py` MockAdapter — 简单文本返回场景可用
- `framework/agent_framework/tools/builtin/__init__.py` — `create_builtin_registry()` 创建含安全工具的真实注册表

### Established Patterns
- AgentLoop 集成测试模式：FakeAdapter + side_effect 序列 → run loop → collect events → assert event types
- monkeypatch 模式：`monkeypatch.setattr(asyncio, "sleep", ...)` 控制时序
- 测试组织：class-based `Test{Feature}` 分组，`_` 前缀 helper 函数
- fixture 约定：定义在使用文件内，仅 MockAdapter 和 memory_dir 放 conftest.py

### Integration Points
- `_loop` 通过 `asyncio.create_task` 启动 → 需要 `asyncio.sleep` mock 控制轮询
- `_loop` 内创建 `AgentLoop` 实例 → 需要 mock `AgentLoop.__init__` 或 `AgentLoop.run`
- AgentLoop → ToolRouter → safe_path 链路需要真实 `create_builtin_registry()` + `ToolRouter` + `FakeAdapter`
- PermissionPipeline 是纯同步代码 → 无需 async 测试

</code_context>

<specifics>
## Specific Ideas

无特定参考 — 测试补充遵循现有测试模式，不引入新模式或框架。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 5-测试覆盖补充*
*Context gathered: 2026-05-29*
