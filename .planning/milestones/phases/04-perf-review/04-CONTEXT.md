# Phase 4: 性能与数据安全审查 - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

修复影响数据安全的性能问题，记录其他性能优化建议，产出 PERF-REVIEW.md。

**修复项（代码改动 + 测试）：**
1. MessageBus inbox 非原子读写 — `read_inbox` 先读后清零，进程崩溃会导致消息丢失
2. MCP transport `_read_until_header_end` 逐字节读取 — `read(1)` 系统调用开销大

**记录项（仅文档，不改代码）：**
3. 同步文件 I/O 阻塞 async 事件循环 — memory 子系统和 team bus 使用同步 I/O
4. TaskManager 全量扫描 — 每次查询都 `glob("task_*.json")` 读取所有文件

**产出：** PERF-REVIEW.md

**不包含：**
- 安全问题（Phase 2 已完成）
- 架构问题（Phase 3 已完成）
- 测试覆盖补充（Phase 5 范围）
- Context compaction LLM 调用开销（非数据安全，记录即可）

</domain>

<decisions>
## Implementation Decisions

### MessageBus 原子读写（数据安全修复）
- **D-01:** 使用 rename swap 方案实现原子清零 — 写空内容到临时文件，然后 `os.replace(temp, path)` 覆盖原文件。框架已有 `_atomic_write` 先例（`memory/index_manager.py`）
- **D-02:** 原子清零失败时不重试，仅 `logger.warning`。已读取的消息保留在内存中返回给调用者，下次 `read_inbox` 会重复读取这些消息，但不丢失。与 Phase 1 D-02 策略一致
- **D-03:** 原子读写测试追加到 `test_teams_bus.py`，保持测试组织一致

### MCP 逐字节读取修复
- **D-04:** 将 `_read_until_header_end` 从 `read(1)` 逐字节改为 `readline()` 循环。asyncio StreamReader 自带缓冲区，连续读到空行（`\r\n`）即检测到 header 结束。大幅减少系统调用次数
- **D-05:** MCP header 读取修复测试追加到 `test_mcp_transport.py`

### PERF-REVIEW.md 报告格式
- **D-06:** 沿用 SECURITY-REVIEW.md 的精简格式 — 每个问题含「描述 + 文件位置 + 严重性 + 修复状态」。与已有报告风格保持一致
- **D-07:** 报告内部按修复状态分两大区域：「已修复」和「已记录」，每个区域内部按严重性排列。清晰区分代码修复项和纯文档项

### Claude's Discretion
- rename swap 的临时文件命名和清理策略
- readline() 循环的具体实现细节（如空行检测逻辑）
- PERF-REVIEW.md 中每个性能问题的具体描述措辞
- 测试函数命名和 fixture 使用方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 性能问题详情
- `.planning/codebase/CONCERNS.md` §Performance Concerns — 5 个性能问题的触发条件、文件位置、影响分析
- `.planning/REQUIREMENTS.md` §R4: 性能审查 — 验收标准和已知性能问题列表
- `.planning/ROADMAP.md` §Phase 4 — 任务列表和验证标准

### 已有报告格式参考
- `docs/reviews/SECURITY-REVIEW.md` — Phase 2 产出的安全审查报告，PERF-REVIEW.md 参照其格式
- `.planning/phases/03-arch-review/` — Phase 3 架构审查报告目录结构

### 核心源文件（修复目标）
- `framework/agent_framework/teams/bus.py:33-48` — `read_inbox` 非原子读写（修复目标 #1）
- `framework/agent_framework/tools/mcp/transport.py:122-129` — `_read_until_header_end` 逐字节读取（修复目标 #2）
- `framework/agent_framework/memory/index_manager.py` — 已有 `_atomic_write` 先例可参考

### 记录项源文件（仅文档）
- `framework/agent_framework/memory/log_manager.py:44-45` — 同步 `Path.read_text()` 阻塞
- `framework/agent_framework/tasks/manager.py:139-146,158-168` — `_load_all()` 全量扫描
- `framework/agent_framework/tools/context/compactor.py:126-156` — Context compaction LLM 调用

### 架构与代码结构
- `.planning/codebase/ARCHITECTURE.md` — 模块依赖关系和数据流
- `.planning/codebase/STRUCTURE.md` — 文件结构、模块位置
- `.planning/codebase/CONVENTIONS.md` — 编码规范

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/agent_framework/memory/index_manager.py` — 已有 `_atomic_write` 实现（写临时文件 + `os.replace`），MessageBus 原子清零可直接参考
- `framework/tests/test_teams_bus.py` — MessageBus 现有测试，原子读写测试可追加
- `framework/tests/test_mcp_transport.py` — MCP transport 现有测试，header 读取测试可追加
- `docs/reviews/SECURITY-REVIEW.md` — 报告格式模板，PERF-REVIEW.md 直接复用其结构

### Established Patterns
- 原子写入模式：写临时文件 → `os.replace(temp, target)` → 原子替换
- 工具错误模式：所有工具返回 `ToolResult(is_error=True)` 而非抛异常
- 报告分级：HIGH/MEDIUM/LOW 三级，与 SECURITY-REVIEW.md 和 ARCH-REVIEW.md 一致
- asyncio StreamReader：自带缓冲区的异步读取，readline() 比逐字节 read(1) 高效

### Integration Points
- `bus.py:37-38` — `read_text()` + `write_text("")` 需替换为 rename swap
- `transport.py:123-129` — `read(1)` 循环需替换为 `readline()` 循环
- PERF-REVIEW.md 应放在 `docs/reviews/` 目录下，与其他审查报告一致

</code_context>

<specifics>
## Specific Ideas

无特定参考 — 修复方案遵循最小改动原则，仅修复性能/数据安全问题本身，不做额外重构。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 4-性能与数据安全审查*
*Context gathered: 2026-05-28*
