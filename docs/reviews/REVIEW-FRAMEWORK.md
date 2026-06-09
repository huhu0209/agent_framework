# Framework Code Review Report

**Audit Date:** 2026-06-09
**Scope:** `framework/agent_framework/` (full framework layer, ~100 files, ~10,475 lines)
**Auditor:** Automated ruff scan + manual review (Phase 12, Plans 01-04)
**Tools:** ruff 0.15.16 (pyflakes F / flake8-bandit S / McCabe C901 / PLR0913) + manual code inspection

---

## ruff Auto-Scan Baseline

Four ruff scan categories were run against `framework/agent_framework/` (excluding tests/):

### F Series: Dead Code (Unused Imports / Variables / Undefined Names)

**32 pyflakes errors found:**

| # | Rule | File | Line | Description |
|---|------|------|------|-------------|
| 1 | F401 | `agents/agent_loop.py` | 9 | `dataclasses.field` imported but unused |
| 2 | F821 | `agents/agent_loop.py` | 288 | Undefined name `logger` — `logging.getLogger(__name__)` not declared |
| 3 | F401 | `agents/config.py` | 9 | `agent_framework.agents.base.Agent` imported but unused |
| 4 | F401 | `agents/reflection.py` | 9 | `typing.Any` imported but unused |
| 5 | F401 | `agents/sub_agent.py` | 6 | `agent_framework.agents.base.Agent` imported but unused |
| 6 | F401 | `hooks/manager.py` | 13 | `typing.Any` imported but unused |
| 7 | F821 | `llm/base.py` | 173 | Undefined name `httpx` — used in type annotation outside `TYPE_CHECKING` guard |
| 8 | F401 | `llm/providers/anthropic_provider.py` | 29 | `..base.InvalidRequestError` imported but unused |
| 9 | F401 | `llm/providers/anthropic_provider.py` | 30 | `..base.LLMAdapterError` imported but unused |
| 10 | F401 | `llm/providers/anthropic_provider.py` | 31 | `..base.RateLimitError` imported but unused |
| 11 | F401 | `llm/providers/anthropic_provider.py` | 44 | `..types.ContentBlock` imported but unused |
| 12 | F401 | `llm/providers/anthropic_provider.py` | 45 | `..types.Message` imported but unused |
| 13 | F401 | `llm/providers/anthropic_provider.py` | 49 | `..types.ThinkingBlock` imported but unused |
| 14 | F401 | `llm/providers/deepseek_provider.py` | 19 | `json` imported but unused |
| 15 | F401 | `llm/providers/deepseek_provider.py` | 27 | `..base.LLMAdapterError` imported but unused |
| 16 | F401 | `llm/providers/deepseek_provider.py` | 28 | `..base.ServiceUnavailableError` imported but unused |
| 17 | F401 | `llm/providers/openai_provider.py` | 15 | `json` imported but unused |
| 18 | F401 | `llm/providers/openai_provider.py` | 25 | `..base.InvalidRequestError` imported but unused |
| 19 | F401 | `llm/providers/openai_provider.py` | 26 | `..base.LLMAdapterError` imported but unused |
| 20 | F401 | `llm/providers/openai_provider.py` | 27 | `..base.RateLimitError` imported but unused |
| 21 | F401 | `llm/providers/openai_provider.py` | 41 | `..types.Message` imported but unused |
| 22 | F401 | `llm/providers/openai_provider.py` | 45 | `..types.UsageStats` imported but unused |
| 23 | F401 | `llm/retry.py` | 31 | `.base.ServiceUnavailableError` imported but unused |
| 24 | F401 | `llm/streaming.py` | 18 | `typing.Any` imported but unused |
| 25 | F401 | `llm/transform/_deepseek.py` | 19 | `._openai._map_openai_stop_reason` imported but unused |
| 26 | F401 | `llm/transform/_deepseek.py` | 19 | `._openai._parse_openai_usage` imported but unused |
| 27 | F401 | `llm/transform/_openai.py` | 33 | `..types.Message` imported but unused |
| 28 | F401 | `orchestrator/worker_agent.py` | 9 | `agent_framework.agents.base.AgentEvent` imported but unused |
| 29 | F401 | `tasks/runner.py` | 9 | `agent_framework.agents.base.Agent` imported but unused |
| 30 | F401 | `teams/manager.py` | 11 | `agent_framework.agents.base.Agent` imported but unused |
| 31 | F401 | `tools/context/token_counter.py` | 6 | `agent_framework.llm.types.AssistantMessage` imported but unused |
| 32 | F401 | `tools/context/token_counter.py` | 16 | `agent_framework.llm.types.UserMessage` imported but unused |

**Note:** No F401 warnings in `__init__.py` re-export files. All F401 hits are in implementation files with genuinely unused imports.

### S Series: Security (flake8-bandit)

**7 security warnings found:**

| # | Rule | File | Line | Description |
|---|------|------|------|-------------|
| 1 | S311 | `llm/retry.py` | 76 | `random.random()` used for jitter — not cryptographic, acceptable |
| 2 | S324 | `memory/semantic_writer.py` | 47 | `hashlib.sha1()` used for filename generation — non-security context |
| 3 | S110 | `tasks/runner.py` | 94 | `try-except-pass` — silent exception swallow |
| 4 | S110 | `tasks/runner.py` | 105 | `try-except-pass` — silent exception swallow |
| 5 | S112 | `teams/bus.py` | 50 | `try-except-continue` — silent exception in message parsing |
| 6 | S110 | `tools/mcp/config.py` | 100 | `try-except-pass` — silent exception on client close |
| 7 | S110 | `viz/ws_server.py` | 41 | `try-except-pass` — silent exception on task result |

### C901: Complexity (McCabe)

**10 high-complexity functions found (threshold: 10):**

| # | Complexity | File | Line | Function |
|---|-----------|------|------|----------|
| 1 | 30 | `agents/agent_loop.py` | 295 | `AgentLoop.run` |
| 2 | 15 | `llm/transform/_normalize.py` | 58 | `_pair_tool_results` |
| 3 | 18 | `tools/router.py` | 58 | `ToolRouter.dispatch` |
| 4 | 14 | `agents/agent_loop.py` | 217 | `AgentLoop._maybe_compact` |
| 5 | 14 | `llm/transform/_deepseek.py` | 22 | `messages_to_deepseek` |
| 6 | 14 | `tasks/tools.py` | 18 | `create_task_tools` |
| 7 | 13 | `llm/providers/anthropic_provider.py` | 144 | `AnthropicProvider.parse_event` |
| 8 | 13 | `llm/streaming.py` | 88 | `StreamingParser.parse_chunk` |
| 9 | 13 | `tools/builtin/memory_tools.py` | 42 | `handle_memory_search` |
| 10 | 11 | `tasks/manager.py` | 185 | `TaskManager._apply_changes` |

### PLR0913: Too Many Parameters

**7 functions with excessive parameter count (threshold: 5):**

| # | Parameters | File | Line | Function |
|---|-----------|------|------|----------|
| 1 | 19 | `agents/agent_loop.py` | 69 | `AgentLoop.__init__` |
| 2 | 8 | `agents/sub_agent.py` | 27 | `run_subagent` |
| 3 | 7 | `llm/resilient.py` | 153 | `create_adapter` |
| 4 | 7 | `tasks/runner.py` | 22 | `TaskRunner.__init__` |
| 5 | 6 | `agents/plan_and_solve.py` | 33 | `PlanAndSolveAgent.__init__` |
| 6 | 6 | `agents/reflection.py` | 93 | `ReflectionAgent.__init__` |
| 7 | 6 | `orchestrator/engine.py` | 30 | `OrchestratorEngine.__init__` |

---

## llm/

### CRITICAL

*(none found)*

### HIGH

#### FRMW-SEC-01: httpx 引用在 TYPE_CHECKING guard 外使用

**Description:** `handle_http_error` 函数参数 `response: "httpx.Response"` 引用了 `httpx`，但 `httpx` 仅在 `TYPE_CHECKING` guard 内导入。运行时 `httpx` 名称未定义，若在非类型检查上下文直接引用会导致 `NameError`。

**File Location:** `framework/agent_framework/llm/base.py:173`

**Impact:** 虽然当前使用字符串注解 `"httpx.Response"` 避免了运行时 NameError，但这是一个设计不一致 — 函数依赖 `httpx.Response` 类型但模块级没有运行时导入。如果 `from __future__ import annotations` 被移除，将立即触发 NameError。

**Fix Suggestion:** 将 `httpx` 导入移到 `TYPE_CHECKING` guard 之外，或确认 `from __future__ import annotations` 始终存在且不会被意外移除。

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-SEC-02: Anthropic Provider 导入 6 个未使用符号

**Description:** `anthropic_provider.py` 导入了 6 个从未在文件中使用的符号：`InvalidRequestError`、`LLMAdapterError`、`RateLimitError`、`ContentBlock`、`Message`、`ThinkingBlock`。这些可能是历史遗留的 import 或为未来预留。

**File Location:** `framework/agent_framework/llm/providers/anthropic_provider.py:29-49`

**Impact:** 增加 import 解析时间，降低代码可读性，误导开发者认为这些类型在本文件中被使用。

**Fix Suggestion:** 移除所有未使用的 import。如果 `InvalidRequestError`/`LLMAdapterError`/`RateLimitError` 是为了 `handle_http_error` 的 re-export 而导入的，改用在调用处直接 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-SEC-03: DeepSeek Provider 导入 3 个未使用符号

**Description:** `deepseek_provider.py` 导入了 `json`、`LLMAdapterError`、`ServiceUnavailableError`，均未在文件中使用。

**File Location:** `framework/agent_framework/llm/providers/deepseek_provider.py:19,27-28`

**Impact:** 同 FRMW-SEC-02。

**Fix Suggestion:** 移除未使用 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-SEC-04: OpenAI Provider 导入 5 个未使用符号

**Description:** `openai_provider.py` 导入了 `json`、`InvalidRequestError`、`LLMAdapterError`、`RateLimitError`、`Message`、`UsageStats`，均未在文件中使用。

**File Location:** `framework/agent_framework/llm/providers/openai_provider.py:15,25-27,41,45`

**Impact:** 同 FRMW-SEC-02。

**Fix Suggestion:** 移除未使用 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-SEC-05: retry.py 导入未使用的 ServiceUnavailableError

**Description:** `retry.py` 导入了 `ServiceUnavailableError` 但从未使用。`retry_with_backoff` 仅检查 `error.retryable` 标志，不引用具体异常类型。

**File Location:** `framework/agent_framework/llm/retry.py:31`

**Impact:** 同 FRMW-SEC-02。

**Fix Suggestion:** 移除未使用 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-SEC-06: streaming.py 导入未使用的 typing.Any

**Description:** `streaming.py` 导入了 `typing.Any` 但从未在文件中使用。

**File Location:** `framework/agent_framework/llm/streaming.py:18`

**Impact:** 代码噪音。

**Fix Suggestion:** 移除未使用 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

### MEDIUM

#### FRMW-DEAD-01: _deepseek.py 导入 _openai.py 的两个内部函数但未使用

**Description:** `llm/transform/_deepseek.py` 从 `._openai` 导入了 `_map_openai_stop_reason` 和 `_parse_openai_usage`，但两者都未使用。这可能是因为 DeepSeek 转换器有独立的实现（`_map_deepseek_stop_reason`、`_parse_deepseek_usage`），但复制代码时遗留了 OpenAI 版本的 import。

**File Location:** `framework/agent_framework/llm/transform/_deepseek.py:19`

**Impact:** 增加 coupling 到 `_openai.py` 的内部实现，如果 `_openai.py` 修改了这些函数签名可能导致 import 错误。

**Fix Suggestion:** 移除两个未使用的 import。

**Priority:** MEDIUM
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-DEAD-02: _openai.py 运行时 import 未使用的 Message 类型

**Description:** `llm/transform/_openai.py:33` 中 `messages_to_openai` 函数内部 `from ..types import Message, SystemMessage, ToolMessage`，但 `Message` 未使用（仅用了 `SystemMessage` 和 `ToolMessage`）。

**File Location:** `framework/agent_framework/llm/transform/_openai.py:33`

**Impact:** 运行时每次调用函数都会执行 import 语句（虽然 Python 缓存），误导代码阅读者。

**Fix Suggestion:** 从 import 中移除 `Message`。

**Priority:** MEDIUM
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-SEC-07: random.random() 用于 jitter 计算（非加密场景）

**Description:** `retry_with_backoff` 使用 `random.random()` 计算 jitter 值避免雷群效应。ruff S311 标记此为不安全的随机数生成器，但在 jitter 计算场景下不需要加密安全随机数。

**File Location:** `framework/agent_framework/llm/retry.py:76`

**Impact:** 无实际安全风险。jitter 仅用于退避策略，不涉及加密或认证。

**Fix Suggestion:** 无需修改。若需要消除 S311 告警，可添加 `# noqa: S311` 注释。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

### LOW

*(pending manual review — additional findings from Task 2)*

---

## tools/

*(pending manual review — Plan 02)*

### CRITICAL

*(pending)*

### HIGH

#### FRMW-DEAD-03: token_counter.py 导入未使用的 AssistantMessage 和 UserMessage

**Description:** `tools/context/token_counter.py` 导入了 `AssistantMessage` 和 `UserMessage` 但从未使用。

**File Location:** `framework/agent_framework/tools/context/token_counter.py:6,16`

**Impact:** 代码噪音，增加不必要的 import 解析。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## agents/

*(pending manual review — Plan 02)*

### CRITICAL

*(pending)*

### HIGH

#### FRMW-SEC-08: agent_loop.py 中 logger 未定义导致运行时 NameError

**Description:** `agent_loop.py:288` 使用 `logger.debug(...)` 但文件中没有 `logging.getLogger(__name__)` 声明。当 memory flush 的 except 分支触发时，会抛出 `NameError: name 'logger' is not defined`，掩盖原始异常。

**File Location:** `framework/agent_framework/agents/agent_loop.py:288`

**Impact:** Memory flush 失败时不仅无法记录日志，还会抛出未处理的 NameError。虽然外层有 try-except，但这违反了错误处理的意图。

**Fix Suggestion:** 在文件顶部添加 `import logging` 和 `logger = logging.getLogger(__name__)`。

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-DEAD-04: agent_loop.py 导入未使用的 dataclasses.field

**Description:** `dataclasses.field` 被导入但未使用。文件中的 `@dataclass` 装饰器不需要 `field`。

**File Location:** `framework/agent_framework/agents/agent_loop.py:9`

**Impact:** 代码噪音。

**Fix Suggestion:** 移除 `field` 从 import 中。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-DEAD-05: config.py、sub_agent.py 导入未使用的 Agent 类

**Description:** `agents/config.py:9` 和 `agents/sub_agent.py:6` 都导入了 `agent_framework.agents.base.Agent` 但未使用。`Agent` 是一个空文件（0 行），本身就是一个 stub。

**File Location:** `framework/agent_framework/agents/config.py:9`, `framework/agent_framework/agents/sub_agent.py:6`

**Impact:** 依赖一个空文件中的空类，增加了不必要的 coupling。

**Fix Suggestion:** 移除 `Agent` 的 import。如果 `Agent` 类被设计为未来基类，应在 `base.py` 中实现后再导入。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-DEAD-06: reflection.py 导入未使用的 typing.Any

**Description:** `agents/reflection.py` 导入了 `typing.Any` 但从未使用。

**File Location:** `framework/agent_framework/agents/reflection.py:9`

**Impact:** 代码噪音。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## teams/

*(pending manual review — Plan 03)*

### CRITICAL

*(pending)*

### HIGH

#### FRMW-DEAD-07: manager.py 导入未使用的 Agent 类

**Description:** `teams/manager.py` 导入了 `agent_framework.agents.base.Agent` 但未使用。

**File Location:** `framework/agent_framework/teams/manager.py:11`

**Impact:** 同 FRMW-DEAD-05。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

### MEDIUM

#### FRMW-SEC-09: bus.py 静默跳过消息解析异常

**Description:** `teams/bus.py:50` 使用 `try-except-continue` 静默跳过无法解析的 JSONL 行。ruff S112 标记此模式。虽然 bus 设计上可能容错坏行，但完全静默可能导致消息丢失无法追踪。

**File Location:** `framework/agent_framework/teams/bus.py:50`

**Impact:** 损坏的消息被静默丢弃，无法在日志中追踪丢失原因。

**Fix Suggestion:** 添加 `logger.debug` 记录跳过的行内容，或在计数器中记录。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

### LOW

*(pending)*

---

## memory/

*(pending manual review — Plan 03)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

#### FRMW-SEC-10: semantic_writer.py 使用 sha1 哈希生成文件名

**Description:** `memory/semantic_writer.py:47` 使用 `hashlib.sha1()` 从语义记忆名称生成文件名 slug。ruff S324 标记此为不安全哈希。但此场景仅用于生成唯一文件名，不涉及安全验证。

**File Location:** `framework/agent_framework/memory/semantic_writer.py:47`

**Impact:** 无实际安全风险。sha1 仅用于生成确定性文件名，不用于认证或完整性验证。

**Fix Suggestion:** 可替换为 `hashlib.sha256()` 或 `hashlib.md5()` 消除 S324 告警，但不影响正确性。也可添加 `# noqa: S324`。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

### LOW

*(pending)*

---

## safety/

*(pending manual review — Plan 03)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## orchestrator/

*(pending manual review — Plan 02)*

### CRITICAL

*(pending)*

### HIGH

#### FRMW-DEAD-08: worker_agent.py 导入未使用的 AgentEvent

**Description:** `orchestrator/worker_agent.py` 导入了 `agent_framework.agents.base.AgentEvent` 但未使用。

**File Location:** `framework/agent_framework/orchestrator/worker_agent.py:9`

**Impact:** 代码噪音，增加不必要的 coupling。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## hooks/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

#### FRMW-DEAD-09: manager.py 导入未使用的 typing.Any

**Description:** `hooks/manager.py` 导入了 `typing.Any` 但从未使用。

**File Location:** `framework/agent_framework/hooks/manager.py:13`

**Impact:** 代码噪音。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## skills/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## tasks/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

#### FRMW-DEAD-10: runner.py 导入未使用的 Agent 类

**Description:** `tasks/runner.py` 导入了 `agent_framework.agents.base.Agent` 但未使用。

**File Location:** `framework/agent_framework/tasks/runner.py:9`

**Impact:** 同 FRMW-DEAD-05。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-SEC-11: runner.py 两处 try-except-pass 静默吞异常

**Description:** `tasks/runner.py` 在任务超时通知和异常通知的 except 分支中使用 `try-except-pass`（行 94 和 105）。这两个 try-except 保护的是"通知写入"操作，通知失败不应中断主流程，但完全静默使得调试困难。

**File Location:** `framework/agent_framework/tasks/runner.py:94,105`

**Impact:** 通知失败时无法通过日志追踪原因。

**Fix Suggestion:** 添加 `logger.debug` 记录通知失败。

**Priority:** HIGH
**Related:** FRMW-04 (安全审查)

---

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## commands/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## prompts/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## a2a/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## transcript/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

*(pending)*

### LOW

*(pending)*

---

## viz/

*(pending manual review — Plan 04)*

### CRITICAL

*(pending)*

### HIGH

*(pending)*

### MEDIUM

#### FRMW-SEC-12: ws_server.py try-except-pass 静默吞异常

**Description:** `viz/ws_server.py:41` 在 WebSocket task result 处理中使用 `try-except-pass`。这是 cleanup 代码中的异常保护，静默处理有一定合理性（防止清理失败阻塞主流程），但缺少日志记录。

**File Location:** `framework/agent_framework/viz/ws_server.py:41`

**Impact:** WebSocket 连接清理失败时无法追踪。

**Fix Suggestion:** 添加 `logger.debug` 记录清理失败。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

### LOW

*(pending)*
