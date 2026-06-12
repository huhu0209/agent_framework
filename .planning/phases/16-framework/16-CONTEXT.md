# Phase 16: Framework 安全修复 - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

修复 v0.0.4 审查中发现的 8 个 framework 安全漏洞（FW-SEC-02~09）：同步 I/O 阻塞事件循环、MCP 环境变量泄露、Skill/Profile 注入防护、WebSocket 无认证、try-except-pass 静默吞异常。

修复范围仅限 framework/agent_framework/，不涉及 backend/ 或 frontend/。

</domain>

<decisions>
## Implementation Decisions

### 异步 I/O 策略（FW-SEC-02, FW-SEC-07）
- **D-01:** 使用 aiofiles 替换所有同步文件 I/O — memory/ 全模块（~10 个文件）+ tools/context/result_truncator.py，统一使用 `aiofiles` 异步读写。需在 framework/pyproject.toml 添加 aiofiles 依赖
- **D-02:** 将所有同步 I/O 函数签名改为 `async def` — `EpisodicLogManager.append()`、`read_log()`、`write_raw()`、`IndexManager._atomic_write()`、`remove()`、`SemanticWriter._create()`、`_merge()`、`Retriever._scan_candidates()`、文件内容读取、`truncate_if_needed()` 等
- **D-03:** 所有调用这些函数的上层方法也需相应改为 async — `MemoryStore.search()`、`flush()`、`ToolExecutor.execute()` 中的截断逻辑等

### MCP 环境变量策略（FW-SEC-03, FW-SEC-08）
- **D-04:** 采用白名单机制 — MCP 子进程只继承必要环境变量（PATH、HOME、TEMP/TMP、USER、LANG）加上 config 中显式声明的 env 字段。不再继承完整 os.environ
- **D-05:** 扩展 `_BLOCKED_ENV_PATTERNS` — 在白名单基础上，对 config 中显式声明的 env 仍做敏感 key 过滤（扩展增加 auth、session、cookie、bearer、refresh、jwt 模式）
- **D-06:** transport.py 的 env 构建逻辑重构 — 从 `{**os.environ, **(self._env or {})}` 改为白名单 + 验证后 config env

### 注入防御策略（FW-SEC-04, FW-SEC-05）
- **D-07:** PromptAssembler 使用 XML 标签包裹各 PromptBlock — 用 `<instruction>...</instruction>`、`<context>...</context>`、`<identity>...</identity>` 等标签包裹各 block，帮助 LLM 区分指令来源
- **D-08:** SkillRegistry 不做内容扫描 — 只做边界标记（XML tag），不做 injection 模式检测。误报风险过高，且 skill 内容通常由开发者控制
- **D-09:** 对 `user_context` 字段添加来源标记 — 在 assembler 中对不可信来源的内容添加额外的 `<user-provided>` 标签，让 LLM 知道该部分内容不受信任

### WebSocket 认证（FW-SEC-06）
- **D-10:** 添加可配置 token 认证 — WebSocket 握手阶段通过 URL 参数 `?token=xxx` 验证客户端身份。token 通过 `serve_ws()` 参数传入，默认为 None（无认证，向后兼容）
- **D-11:** 在 serve_ws 启动时打印认证状态日志 — 有 token 时记录 "WebSocket auth enabled"，无 token 时记录 "WebSocket running without auth (development mode)"

### try-except-pass 修复（FW-SEC-09）
- **D-12:** 4 处 try-except-pass 全部改为 logger.debug/warning 记录 — teams/bus.py:50（logger.debug + 跳过行内容）、tasks/runner.py:94,105（logger.debug 通知失败）、tools/mcp/config.py:100（logger.debug client 关闭失败）、viz/ws_server.py:41（logger.debug task cleanup 失败）

### Plan 分组策略
- **D-13:** 按问题类型分 4 个 plan：
  - Plan A: 同步 I/O → async（FW-SEC-02 memory/ + FW-SEC-07 result_truncator）— 工作量最大
  - Plan B: MCP 环境变量白名单（FW-SEC-03 transport + FW-SEC-08 config filter）
  - Plan C: 注入防护（FW-SEC-04 Skill + FW-SEC-05 Profile assembler）
  - Plan D: WebSocket token 认证（FW-SEC-06）+ try-except-pass 修复（FW-SEC-09）

### 验证策略
- **D-14:** 全量 pytest 验证 — 每个 plan 完成后运行 `cd framework && pytest tests/ -v` 确认 964+ 测试通过
- **D-15:** ruff 安全扫描 — `ruff check --select S framework/` 确认修复的 S 系列警告已消除

### Claude's Discretion
- aiofiles 的具体 API 调用方式（async with open vs aiofiles.open）
- XML 标签的具体命名和格式
- MCP 白名单的具体最小环境变量列表
- WebSocket token 验证的具体实现方式
- 每个 plan 内部的修复顺序

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查报告（问题来源）
- `docs/reviews/REVIEW-FRAMEWORK.md` — 全部 FRMW-SEC issue 详情（含文件位置、影响分析、修复建议）
  - FRMW-ARCH-20 (memory/ 同步 I/O, HIGH)
  - FRMW-SEC-13 (result_truncator.py 同步 I/O, HIGH)
  - FRMW-SEC-16 (MCP env 继承, MEDIUM)
  - FRMW-SEC-15 (MCP env 过滤不完整, MEDIUM)
  - FRMW-SEC-25 (Skill 注入, HIGH)
  - FRMW-SEC-28 (Profile prompt injection, HIGH)
  - FRMW-SEC-30 (WebSocket 无认证, HIGH)
  - FRMW-SEC-09 (bus.py try-except-continue, MEDIUM)
  - FRMW-SEC-11 (runner.py try-except-pass ×2, HIGH)
  - FRMW-SEC-12 (ws_server.py try-except-pass, MEDIUM)
  - FRMW-SEC-17 (mcp config.py try-except-pass, MEDIUM)

### 需求定义
- `.planning/REQUIREMENTS.md` — FW-SEC-02~09 需求定义
- `.planning/ROADMAP.md` — Phase 16 目标、成功标准、范围定义

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Import 组织、TYPE_CHECKING guard、logging 模式
- `.planning/codebase/ARCHITECTURE.md` — 架构层次、数据流、关键抽象

### 已知问题
- `.planning/codebase/CONCERNS.md` — 安全问题详情（MCP env 注入、同步 I/O、WebSocket 认证）

### 框架源码（修改目标）
- `framework/agent_framework/memory/` — 全模块同步 I/O 改 async（~10 个文件）
- `framework/agent_framework/tools/context/result_truncator.py` — 同步文件写入改 async
- `framework/agent_framework/tools/mcp/transport.py` — env 构建逻辑白名单化
- `framework/agent_framework/tools/mcp/config.py` — _BLOCKED_ENV_PATTERNS 扩展 + try-except
- `framework/agent_framework/skills/registry.py` — Skill 内容安全处理
- `framework/agent_framework/prompts/assembler.py` — XML 标签边界标记
- `framework/agent_framework/viz/ws_server.py` — token 认证 + try-except
- `framework/agent_framework/teams/bus.py` — try-except-continue 改 logger
- `framework/agent_framework/tasks/runner.py` — try-except-pass 改 logger

### Phase 15 上下文（前置依赖）
- `.planning/phases/15-framework/15-CONTEXT.md` — 死代码清理已完成，Phase 16 依赖已满足

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/agent_framework/memory/index_manager.py` — 已有 `_atomic_write()` 使用 rename 模式，可直接改为 aiofiles 版本
- `framework/agent_framework/safety/boundary.py` — 已有 `safe_path()` 沙箱函数，可作为安全修复的参考模式
- logging 模式 — 所有模块使用 `logger = logging.getLogger(__name__)`，try-except 修复直接复用

### Established Patterns
- 框架全部 async — 所有公共方法都是 `async def`，同步 I/O 是唯一例外（本 phase 修复）
- `asyncio.Lock` 用于协程级互斥 — TaskManager 已使用
- Pydantic BaseModel 用于配置 — McpServerConfig 已有 env 字段验证模式
- WebSocket 使用 websockets 库 — serve_ws 已有基础结构，只需添加 auth 层

### Integration Points
- aiofiles 需添加到 framework/pyproject.toml 依赖
- memory/ 改 async 后，所有调用方（AgentLoop、MemoryStore、ToolExecutor）需相应更新
- MCP env 白名单可能影响现有 MCP 工具的兼容性（需要测试）
- WebSocket token 认证需在 backend 启动 serve_ws 时传入 token

</code_context>

<specifics>
## Specific Ideas

- memory/ 模块有 ~10 个文件需改 async，其中 store.py、log_manager.py、retriever.py 是主要目标
- aiofiles 在 Python 社区广泛使用（GitHub 1.3k+ stars），异步文件 I/O 的事实标准
- MCP 白名单的最小集：PATH、HOME、TEMP/TMPDIR、USER、LANG、SYSTEMROOT(Windows)
- XML 边界标记可参考 Anthropic 的 prompt engineering 最佳实践（使用 XML tag 分隔指令）
- 4 个 plan 的依赖关系：Plan A（async I/O）无依赖可先行，Plan B/C/D 互相独立可并行

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-Framework 安全修复*
*Context gathered: 2026-06-10*
