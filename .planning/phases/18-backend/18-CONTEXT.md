# Phase 18: Backend 全面修复 - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

修复 v0.0.4 审查中发现的 10 个 backend 安全和逻辑问题（BK-SEC-01~05, BK-LOGIC-01~05）：SSE 异常信息泄露、session_id 未验证、CORS 过度宽松、API key 明文存储、Redis 异常静默吞掉、TTL 驱逐竞态、JSONL 非原子读写、共享 ToolUseContext、AgentFactory 缺 working_dir、访问 framework 私有属性。

修复范围仅限 `backend/app/` 和 `backend/main.py`，以及 `framework/agent_framework/agents/agent_loop.py` 中添加一个 @property（D-09）。

</domain>

<decisions>
## Implementation Decisions

### SSE 错误响应策略（BK-SEC-05）
- **D-01:** SSE 错误事件返回分类消息（非 `str(exc)`），基于 `ErrorCategory` 枚举 + 用户友好消息映射表
- **D-02:** 仅 SSE 传输层替换 — `session.messages` 仍存储原始 `str(exc)` 供服务端调试
- **D-03:** 已知错误类型：LLM timeout、LLM rate limit、Tool execution error、Session not found、Unknown。基于异常类型（isinstance）映射到枚举值

### JSONL 原子写入 + 异步化（BK-LOGIC-02, BK-ARCH-08）
- **D-04:** 所有文件 I/O 改 aiofiles async — `update_title`、`delete_session`、`_append_history`、`list_sessions`、`_get_all_messages` 全部改为 `async def`
- **D-05:** SessionManager 全部方法改 async — 包括内部方法（`_get_all_messages`、`_append_history` 等），保持一致性。调用方（chat.py）相应 await
- **D-06:** 原子写入用 aiofiles + temp file + `os.replace` — 与 Phase 16 framework 层策略一致
- **D-07:** 添加 `aiofiles` 到 `backend/pyproject.toml` 依赖

### Framework 接口对接（BK-LOGIC-03, 04, 05, BKND-LOGIC-06）
- **D-08:** 每次 `create_loop()` 创建新 `ToolUseContext()` 实例 — 将 `self._ctx = ToolUseContext()` 从 `__init__` 移到 `create_loop` 内部
- **D-09:** `AgentLoop` 添加 `system_prompt_text` @property — 框架层仅加一个 property，backend 用 `loop.system_prompt_text` 替代 `getattr(loop, '_system_prompt_text', None)`
- **D-10:** `ctx.working_dir = str(storage_dir / "shared_workspace")` — 所有会话共享一个 workspace 目录
- **D-11:** 添加 `SessionManager` 公共方法 `persist_messages()` / `restore_messages()` — 封装 Redis + JSONL 操作，替代 `_redis_set/get_messages` 私有方法访问

### session_id 验证 + Redis 异常 + 安全（BK-SEC-01~04）
- **D-12:** `session_id` path 参数用 FastAPI `Path(pattern=SESSION_ID_RE)` 验证 — 每个端点独立声明，FastAPI 自动返回 422
- **D-13:** Redis 连接异常区分处理 — `redis_lib.ConnectionError` / `TimeoutError` 记录 ERROR 并降级运行；`ValueError`（配置错误）直接 raise 让应用启动失败
- **D-14:** `Settings.llm_api_key` 改为 `SecretStr` — `AgentFactory.from_settings` 调用 `create_adapter` 时用 `get_secret_value()`
- **D-15:** CORS `allow_methods` 收紧为 `["GET", "POST", "DELETE", "PATCH"]`，`allow_headers` 收紧为 `["Content-Type", "X-Session-Id"]`

### TTL 驱逐竞态（BK-LOGIC-01）
- **D-16:** `_evict_expired` 中检查 `session.task` 是否仍在运行 — 活跃会话跳过驱逐（延长 TTL），避免消息丢失

### Plan 分组策略
- **D-17:** 按问题类型和依赖关系分 plan：
  - Plan A: Framework 接口对接 — AgentLoop @property + ToolUseContext 每会话实例 + working_dir + persist/restore 公共方法（BK-LOGIC-03, 04, 05, BKND-LOGIC-06）— 其他 plan 依赖这些接口
  - Plan B: SessionManager 异步化 + 原子写入 — aiofiles 改造 + 原子写入 + TTL 竞态修复（BK-LOGIC-01, 02, BK-ARCH-08）— 工作量最大
  - Plan C: SSE 错误 + 安全修复 — ErrorCategory 枚举 + CORS + session_id 验证 + Redis 异常 + SecretStr（BK-SEC-01~05, BK-SEC-05）

### 验证策略
- **D-18:** 全量 pytest 验证 — 每个 plan 完成后运行 `cd framework && pytest tests/ -v` 确认 964+ 测试通过（framework 层改动影响测试）
- **D-19:** backend 手动验证 — SSE 错误分类、session_id 验证、原子写入行为

### Claude's Discretion
- ErrorCategory 枚举的具体定义和命名
- 用户友好消息的具体文案
- SessionManager 异步化的具体方法拆分和调用链更新
- persist/restore 方法的具体 API 设计
- FastAPI Path() pattern 的具体写法
- 每个 plan 内部的修复顺序

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查报告（问题来源）
- `docs/reviews/REVIEW-BACKEND.md` — 全部 BKND-* issue 详情（含文件位置、影响分析、修复建议、跨层问题）
  - BKND-SEC-01 (CORS wildcard, MEDIUM)
  - BKND-SEC-02 (Redis silent, MEDIUM)
  - BKND-SEC-03 (API key plain str, MEDIUM)
  - BKND-SEC-04 (session_id unvalidated, HIGH)
  - BKND-SEC-05 (SSE str(exc) leak, HIGH)
  - BKND-SEC-06 (No auth, HIGH) — Out of scope（需单独 milestone）
  - BKND-LOGIC-01 (TTL eviction race, HIGH)
  - BKND-LOGIC-02 (JSONL non-atomic, HIGH)
  - BKND-LOGIC-03 (Shared ToolUseContext, MEDIUM→HIGH)
  - BKND-LOGIC-04 (AgentFactory working_dir, MEDIUM)
  - BKND-LOGIC-05 (get() refreshes TTL, LOW) — 不在 phase 范围
  - BKND-LOGIC-06 (私有方法访问, MEDIUM)
  - BKND-ARCH-06 (Shared ctx, same as BKND-LOGIC-03)
  - BKND-ARCH-07 (working_dir, same as BKND-LOGIC-04)
  - BKND-ARCH-08 (sync I/O, LOW → 本 phase 一并处理)
  - BKND-ARCH-10 (private attr access, same as BKND-LOGIC-05)

### 需求定义
- `.planning/REQUIREMENTS.md` — BK-SEC-01~05, BK-LOGIC-01~05 需求定义
- `.planning/ROADMAP.md` — Phase 18 目标、成功标准、范围定义

### 编码规范
- `.planning/codebase/CONVENTIONS.md` — Import 组织、logging 模式
- `.planning/codebase/ARCHITECTURE.md` — 架构层次、数据流
- `.planning/codebase/CONCERNS.md` — Backend 已知问题（CONCERNS.md 中 "Backend scaffold" 条目已过时）

### 框架源码（需改动）
- `framework/agent_framework/agents/agent_loop.py` — 添加 `system_prompt_text` @property（D-09）

### Backend 源码（修改目标）
- `backend/main.py` — CORS 收紧 + Redis 异常区分（D-13, D-15）
- `backend/app/config/__init__.py` — SecretStr 改造（D-14）
- `backend/app/models/__init__.py` — 移除未使用 Field import（BKND-DEAD-01）
- `backend/app/services/agent_factory.py` — 每会话 ctx + working_dir + SecretStr（D-08, D-10, D-14）
- `backend/app/services/session.py` — 全部异步化 + 原子写入 + TTL 竞态 + 公共方法（D-04~07, D-11, D-16）
- `backend/app/api/v1/chat.py` — SSE 错误分类 + session_id 验证 + await 异步方法 + 私有属性替换（D-01~03, D-09, D-12）

### 前序阶段上下文
- `.planning/phases/16-framework/16-CONTEXT.md` — Phase 16 安全修复模式（aiofiles、白名单、try-except → logger）
- `.planning/phases/17-framework/17-CONTEXT.md` — Phase 17 逻辑修复（ToolUseContext TypedDict、方法提取、HITL 注入）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/agent_framework/agents/agent_loop.py` — `AgentLoop` 已有 `_system_prompt_text` 属性，仅需添加 `@property` 暴露
- `framework/agent_framework/tools/types.py` — `ToolUseContext()` 无必填参数，可直接 `ToolUseContext()` 创建新实例
- Phase 16 的 aiofiles 模式 — `memory/` 模块已全部改为 aiofiles async，可作为 SessionManager 异步化的参考模式
- `SESSION_ID_RE` — 已在 `models/__init__.py` 定义，直接在 `Path()` 参数中引用

### Established Patterns
- aiofiles async — Phase 16 已在 framework 层建立，backend 遵循相同模式
- temp file + os.replace 原子写入 — `memory/index_manager.py` 已有 `_atomic_write()` 参考实现
- Pydantic SecretStr — framework 的 provider 层使用 `_api_key` 私有存储，backend 改用 SecretStr 更安全
- FastAPI Path() 验证 — 标准做法，无需额外依赖

### Integration Points
- AgentLoop @property 改动需确保 framework 964+ 测试通过
- SessionManager 全部 async 后，chat.py 所有调用点需加 `await`
- `persist_messages()` 公共方法需替代 chat.py 中 `asyncio.to_thread(sm._redis_set_messages, ...)` 调用
- `create_adapter()` 接受 `api_key: str`，`AgentFactory.from_settings` 需调用 `get_secret_value()` 转换
- aiofiles 需添加到 `backend/pyproject.toml` 依赖

</code_context>

<specifics>
## Specific Ideas

- ErrorCategory 枚举建议值：`LLM_TIMEOUT`、`LLM_RATE_LIMIT`、`TOOL_ERROR`、`SESSION_NOT_FOUND`、`UNKNOWN_ERROR`
- SessionManager 公共方法命名：`persist_messages(session_id, messages)` 替代 `_redis_set_messages`，`restore_messages(session_id)` 替代 `_redis_get_messages`
- FastAPI Path pattern：`session_id: str = Path(pattern=r"^[0-9a-f]{32}$")`
- CORS 实际使用：methods `GET`（history/list）、`POST`（chat）、`DELETE`（delete）、`PATCH`（rename）；headers `Content-Type`（JSON body）、`X-Session-Id`（响应头，可能不需在 request headers 中）
- BKND-DEAD-01（Field unused import）和 BKND-ARCH-09（SSE drops unknown stop reason）虽然是 LOW/MEDIUM，可在修改 chat.py 时一并顺手修复

</specifics>

<deferred>
## Deferred Ideas

- BKND-SEC-06 (全部 API 无认证) — 需单独 milestone，架构级改动
- BKND-ARCH-04 (SessionManager 混合职责) — 需较大重构，留后续 milestone
- BKND-ARCH-05 (redis_client: Any | None) — 可在后续引入 Protocol 类型
- BKND-ARCH-01 (create_chat C901=12) — 本次 SSE 错误分类可能增加复杂度，但净增量有限
- BKND-LOGIC-05 (get() 刷新 TTL) — LOW 级别，设计决策留后续
- BKND-ARCH-11 (before 参数类型) — LOW 级别

</deferred>

---

*Phase: 18-Backend 全面修复*
*Context gathered: 2026-06-10*
