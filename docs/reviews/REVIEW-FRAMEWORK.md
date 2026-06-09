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

#### FRMW-LOGIC-01: normalize_messages 中 last.content 在 model_copy(update=...) 前已被 content=list(msg.content) 修改

**Description:** `normalize_messages` 函数在合并同角色消息时（行 44-46），先做 `last.model_copy(update={"content": [*last.content, *msg.content]})`。虽然这里用了 `model_copy` 而非直接赋值（避免了 in-place mutation），但行 31 `msg.model_copy(update={"content": list(msg.content)})` 对每个新消息创建了 content 的浅拷贝。由于 Pydantic BaseModel 的 `content` 是 `list[ContentBlock]`，`list(msg.content)` 只拷贝引用，不拷贝 ContentBlock 对象本身。如果外部代码修改了 ContentBlock 的可变字段（如 `ToolUseBlock.input: dict`），会影响已规范化的消息。

**File Location:** `framework/agent_framework/llm/transform/_normalize.py:31,45`

**Impact:** 大部分 ContentBlock 是 frozen Pydantic model（不可变），但 `ToolUseBlock.input` 是 `dict[str, Any]`（可变）。如果调用方在规范化后修改了 input dict，规范化结果会意外改变。

**Fix Suggestion:** `normalize_messages` 的浅拷贝行为在实际使用中尚未引发 bug（因为调用方通常不修改 input），但违反不可变性原则。如果严格遵循不可变性，应使用 `copy.deepcopy` 或确保 ContentBlock 的可变字段不被外部修改。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-02: _pair_tool_results 插入位置可能错误

**Description:** `_pair_tool_results` 函数在查找缺失 tool_result 的插入位置时，先找最后一个 ToolMessage 的位置（行 89-92），如果找不到，找最后一个 AssistantMessage 的位置（行 94-98）。但插入使用 `insert(insert_idx + 1 + j, placeholder)`，在找到最后一个 ToolMessage 后插入到其后方。如果消息序列是 `[AssistantMsg(tool_use), ToolMsg(A), AssistantMsg(tool_use), (missing B)]`，缺失的 B 会被插入到 A 后面而非第二个 AssistantMsg 后面。在严格协议要求下（tool_result 必须紧跟 tool_use），这可能导致 tool_result 和 tool_use 的配对关系不正确。

**File Location:** `framework/agent_framework/llm/transform/_normalize.py:89-102`

**Impact:** 当存在多个 tool_use 且部分缺失 tool_result 时，placeholder 的插入位置可能不够精确。但实际场景中，通常一个 assistant message 中的所有 tool_use 共享相同的 tool_result 消息，因此位置偏差通常不影响 API 行为。

**Fix Suggestion:** 改为按 tool_use 的位置逐个插入缺失的 tool_result，确保每个 placeholder 紧跟其对应的 assistant message 中的 tool_use。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-03: resilient.py stream() 传输阶段错误不触发重试

**Description:** `ResilientLLMAdapter.stream()` 在重试循环中只捕获连接建立阶段的错误（获取 first_event）。一旦进入传输阶段（`yield first_event` + `async for event in stream`），如果发生 `LLMAdapterError`，会直接 record_failure 并 raise，不会重试。这意味着传输中途的网络断开（如 HTTP 连接超时）会导致整个流失败，无法通过重试恢复。

**File Location:** `framework/agent_framework/llm/resilient.py:94-101`

**Impact:** 流式传输中途失败时，调用方需要自行处理重试（重新发起完整请求）。对于长响应（大量 tool call 参数），中途失败的代价较高（已接收的 token 浪费）。

**Fix Suggestion:** 流式传输中途失败的重试需要 checkpoint 机制（记录已接收位置），实现复杂度较高。当前行为可接受，但应在文档中明确说明流式传输的 retry 仅覆盖连接建立阶段。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-04: CircuitBreaker HALF_OPEN 状态下 success_count 未在 CLOSED 状态重置

**Description:** `CircuitBreaker.record_success()` 在 HALF_OPEN 状态下递增 `_success_count`，达到阈值后转为 CLOSED 并重置 `_failure_count` 和 `_success_count`。但在 CLOSED 状态下（行 227-228），`record_success()` 只重置 `_failure_count = 0`，不清除 `_success_count`。这意味着 `_success_count` 在从 HALF_OPEN 恢复到 CLOSED 后仍然保留之前的计数。但由于 CLOSED 状态下不检查 `_success_count`，这不影响功能正确性。

**File Location:** `framework/agent_framework/llm/retry.py:217-228`

**Impact:** `get_stats()` 在 CLOSED 状态下可能返回非零的 `success_count`，与直觉不符（closed 状态应该没有"探测成功"计数）。不影响状态转换正确性。

**Fix Suggestion:** 在 CLOSED 状态的 `record_success()` 中也重置 `_success_count = 0`。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-ARCH-05: _PROVIDER_MAP 使用字符串路径做动态 import

**Description:** `resilient.py` 中的 `_PROVIDER_MAP` 使用 `"agent_framework.llm.providers.deepseek_provider.DeepSeekProvider"` 这样的字符串路径动态加载 Provider 类。如果模块路径重构（如重命名 provider 文件），`_PROVIDER_MAP` 中的路径会失效，导致运行时 `ImportError`。没有编译时检查。

**File Location:** `framework/agent_framework/llm/resilient.py:137-141,144-150`

**Impact:** 重构时容易遗漏更新 `_PROVIDER_MAP`。目前只有 3 个 provider，维护成本可控。

**Fix Suggestion:** 改用静态导入 + 字典映射（`from .providers.deepseek_provider import DeepSeekProvider`），让 IDE 和类型检查器能发现路径变更。或添加单元测试验证所有 `_PROVIDER_MAP` 条目可正常加载。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

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

#### FRMW-ARCH-01: OpenAI 与 DeepSeek Provider 大量代码重复

**Description:** `openai_provider.py` 和 `deepseek_provider.py` 共享近乎相同的结构：`_build_request_body`、`_parse_response`、`_handle_error`、`complete`、`stream`、`health_check`、`close` 方法的实现几乎一致。两者都使用 `OpenAIStreamParser` 和 `parse_sse_lines`，错误处理逻辑完全相同。唯一的差异是 DeepSeek 额外做了 `_validate_no_image_blocks` 和 thinking 模式参数静默警告。

**File Location:** `framework/agent_framework/llm/providers/openai_provider.py` (全文), `framework/agent_framework/llm/providers/deepseek_provider.py` (全文)

**Impact:** 维护两份几乎相同的代码增加了 bug 风险 — 修复一个 provider 的 bug 时容易忘记同步另一个。当前约 160 行重复代码。

**Fix Suggestion:** 提取 `OpenAICompatProvider` 基类，包含 `complete`/`stream`/`health_check`/`close` 的通用实现。`DeepSeekProvider` 继承它并添加 `_validate_no_image_blocks` 和 thinking 警告逻辑。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-02: health_check 使用完整 API 调用（高成本健康检查）

**Description:** 三个 Provider 的 `health_check` 都发送一个完整的 LLM API 调用（`/v1/messages` 或 `/chat/completions`），消耗 token 并增加延迟。对于频繁的健康检查（如 circuit breaker 探测），每次消耗 1 个 output token + 若干 input token。

**File Location:** `framework/agent_framework/llm/providers/anthropic_provider.py:354-366`, `framework/agent_framework/llm/providers/openai_provider.py:207-219`, `framework/agent_framework/llm/providers/deepseek_provider.py:246-258`

**Impact:** 每次 circuit breaker 探测消耗 API 配额。在高频探测场景下累积成本显著。

**Fix Suggestion:** 改为 HEAD 请求或只检查 DNS + TCP 连接建立。如果 provider API 不支持 HEAD，可检查 `/v1/models` 等轻量端点。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-03: AnthropicStreamParser 仅在 message_delta 输出 TOOL_USE_END

**Description:** `AnthropicStreamParser.parse_event` 仅在 `message_delta` 事件中输出 `TOOL_USE_END` 事件，而不是在 `content_block_stop` 时。这意味着 tool call 的完整参数（包含 JSON 解析后的 input）要等到整个消息结束才可用。如果消息很长（大量 text 后跟 tool_use），调用方需要等待所有 content blocks 结束才能获得 tool call 的解析结果。

**File Location:** `framework/agent_framework/llm/providers/anthropic_provider.py:210-244`

**Impact:** 功能正确，但与 OpenAI 解析器的行为不一致 — OpenAI 解析器在 `finish_reason`（等价于 `message_delta`）时输出 TOOL_USE_END，两者行为实际一致。这是设计选择而非 bug。

**Fix Suggestion:** 无需修改。如果需要更早获得 tool call 完整参数，可在 `content_block_stop` 时输出 TOOL_USE_END（需要缓冲 input_json_delta），但这会增加复杂度。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-DEAD-11: _openai.py 中 messages_to_openai 函数内运行时 import Message

**Description:** `messages_to_openai` 在函数体内部使用 `from ..types import Message, SystemMessage, ToolMessage`，但 `Message` 类型实际未被使用。这个 import 语句在每次调用时都会执行（虽然 Python 会缓存模块）。此外，函数参数类型为 `list` 而非 `list[Message]`，缺少类型注解。

**File Location:** `framework/agent_framework/llm/transform/_openai.py:19,33`

**Impact:** 轻微 — `Message` 导入无用且函数签名类型不精确。

**Fix Suggestion:** 移除 `Message` 导入，将参数类型改为 `list[Message]`。

**Priority:** LOW
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-ARCH-04: StreamCollector.collect() 不验证完整性

**Description:** `StreamCollector.collect()` 返回 CompletionResult 时不验证是否已收到 DONE 事件。如果调用方在流未结束时调用 `collect()`，会得到不完整的结果（可能缺少 tool calls 或 usage 数据）。`collect()` 是同步方法，没有 async 等待机制。

**File Location:** `framework/agent_framework/llm/streaming.py:265-285`

**Impact:** 如果使用不当（在流结束前调用），会返回不完整数据。但当前代码中 `collect()` 仅在流结束后调用，因此实际不影响正确性。

**Fix Suggestion:** 添加 `assert self._done, "collect() called before stream ended"` 或在返回结果中标记 `incomplete=True`。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

## tools/

逐文件审查范围：12 个源文件，~1511 行。
模块职责：工具注册、路由、执行、权限、参数校验、降级、MCP 集成、上下文压缩/截断/token 估算。

### CRITICAL

*(none found)*

### HIGH

#### FRMW-DEAD-03: token_counter.py 导入未使用的 AssistantMessage 和 UserMessage

**Description:** `tools/context/token_counter.py` 导入了 `AssistantMessage` 和 `UserMessage` 但从未使用。这两个类型在文件中没有任何引用点——`_count_message_chars` 使用 `isinstance` 匹配，直接从 `agent_framework.llm.types` 联合类型导入的 `Message` 已覆盖所有消息类型判断。

**File Location:** `framework/agent_framework/tools/context/token_counter.py:6,16`

**Impact:** 代码噪音，增加不必要的 import 解析，误导阅读者认为这些类型在文件中被直接构造或引用。

**Fix Suggestion:** 移除未使用的 import。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-LOGIC-05: router.py ASK 权限决策返回 error 而非触发 HITL

**Description:** `ToolRouter.dispatch()` 行 72-76 中，当 `PermissionPipeline.check()` 返回 `PermissionDecision.ASK` 时，dispatch 返回一个 `is_error=True` 的 ToolResult。这意味着 Agent 在面对需要用户确认的工具调用时，会收到"工具执行失败"的语义，而不是被引导去触发 Human-in-the-Loop (HITL) 交互。ASK 的设计意图应该是暂停执行、等待用户授权后继续，但当前实现等同于拒绝。

**File Location:** `framework/agent_framework/tools/router.py:72-76`

**Impact:** 权限管道的 ASK 决策永远不会生效——Agent 只会看到错误消息并尝试其他路径，不会暂停等待用户确认。这意味着所有"需要确认"的工具实际上都被静默拒绝了。

**Fix Suggestion:** 引入 HITL 机制：ASK 决策时应抛出特定异常（如 `ToolConfirmationRequired`），由 AgentLoop 捕获并暂停执行等待用户输入，而非直接返回错误 ToolResult。或在 ToolResult 中增加 `requires_confirmation=True` 标记，让 AgentLoop 识别并处理。

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-ARCH-06: router.py 4 层职责混合（路由 + 权限 + hook + 降级）

**Description:** `ToolRouter.dispatch()` 方法（行 58-156）承担了 4 项独立职责：(1) 权限检查（行 65-76），(2) PreToolUse hook 触发（行 78-98），(3) 工具执行 + 降级（行 100-135），(4) PostToolUse hook 触发（行 137-155）。这导致 dispatch 方法复杂度达 C901=18，且任何一层的变更都需要修改整个方法。

**File Location:** `framework/agent_framework/tools/router.py:58-156`

**Impact:** dispatch 方法难以测试——单元测试需要 mock 权限管道、hook 管理器、执行器、降级器 4 个依赖。任何一层的行为变更都可能意外影响其他层。

**Fix Suggestion:** 将 dispatch 拆分为管道模式：`_check_permission() -> _run_pre_hooks() -> _execute_with_fallback() -> _run_post_hooks()`，dispatch 只负责编排管道调用。每步返回结构化中间结果（如 `PermissionDecision`、`HookResult`），下游步骤根据上游结果决定是否继续。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-07: _dispatch_agent 返回 hardcoded "not implemented" stub

**Description:** `router.py:179-183` 中 `_dispatch_agent` 方法始终返回 `ToolResult(content="Agent 工具 '{name}' 未实现。子 Agent 支持尚未实现。", is_error=True)`。这是一个永久性 stub——方法签名存在但永远返回错误。如果 LLM 在 tool_use 中生成了 `agent__` 前缀的工具名，dispatch 会正确路由到这里，但用户只会看到晦涩的"未实现"错误，没有引导说明。

**File Location:** `framework/agent_framework/tools/router.py:179-183`

**Impact:** (1) 死代码路径——任何触发 agent__ 前缀的调用都会失败，浪费 token。(2) dispatch 方法中 `name.startswith("agent__")` 的分支增加了认知负担。(3) 如果 agent 功能未来实现，容易忘记更新这个方法。

**Fix Suggestion:** 如果 agent 工具支持确实未实现，应在 registry 层面阻止注册 `agent__` 前缀的工具，或在前端 prompt 中明确告知 LLM 不使用该前缀。否则应添加 TODO 注释和 issue 跟踪。或者干脆移除这个分支，让未知工具统一走 `_dispatch_builtin` 返回"未知工具"。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-06: _CRITICAL_TOOLS 全局集合始终为空，权限 DENY 第一级永远不会触发

**Description:** `safety/permissions.py:40` 定义 `_CRITICAL_TOOLS: set[str] = set()`，这是一个模块级全局空集合。`PermissionPipeline.check()` 行 58 首先检查 `tool_name in _CRITICAL_TOOLS`，但由于集合始终为空，这个检查永远返回 False。整个 DENY 第一级形同虚设——没有任何 API 允许向 `_CRITICAL_TOOLS` 添加工具名。

**File Location:** `framework/agent_framework/safety/permissions.py:40,58`

**Impact:** 安全模型中设计的高危工具强制拒绝机制从未生效。如果未来添加了需要强制拒绝的高危工具（如 `execute_sql`、`delete_all`），没有标准化的方式将其标记为 CRITICAL。

**Fix Suggestion:** (1) 将 `_CRITICAL_TOOLS` 改为可配置（通过 `PermissionPipeline.__init__` 参数或配置文件传入）。(2) 或者移除这个空集合，只保留 profile 级别的 `disallowed_tools` 做黑名单。(3) 如果保留，至少添加 `add_critical_tool()` 函数或类方法允许运行时注册。

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-SEC-13: result_truncator.py 使用同步文件 I/O 阻塞事件循环

**Description:** `tools/context/result_truncator.py:33-35` 中 `truncate_if_needed` 使用 `os.makedirs()` 和 `open(dump_path, "w")` 进行同步文件写入。但这个函数被 `ToolExecutor.execute()` 在 `async` 上下文中调用（行 53），且 `ToolRouter.dispatch()` 也是异步的。当工具结果超过 20000 字符时，同步 I/O 会阻塞事件循环，影响其他并发任务。

**File Location:** `framework/agent_framework/tools/context/result_truncator.py:33-35`

**Impact:** 大型工具结果（如读取大文件、搜索返回大量结果）触发截断时会阻塞整个 asyncio 事件循环，直到文件写入完成。在并发 agent 场景下，一个 agent 的大结果会阻塞其他 agent 的执行。

**Fix Suggestion:** 使用 `aiofiles` 异步文件 I/O，或将文件写入移到 `asyncio.to_thread()` 中执行。同时将 `truncate_if_needed` 改为 `async def truncate_if_needed()`。

**Priority:** HIGH
**Related:** FRMW-04 (安全审查)

---

### MEDIUM

#### FRMW-SEC-14: file_tools.py safe_path 调用完整但缺少符号链接 TOCTOU 说明

**Description:** `file_tools.py` 的 `read_file`（行 20）和 `write_file`（行 39）都正确调用了 `safe_path(path, Path(ctx.working_dir))` 进行路径沙箱验证。`safe_path()` 实现使用了 `resolve()` 处理 `../../` 和符号链接绕过，修复完整。但存在一个理论上的 TOCTOU (Time-of-Check-Time-of-Use) 窗口：在 `safe_path()` 验证通过后、实际文件操作前，攻击者可能创建符号链接指向工作目录外。不过这需要精确时序控制，在当前 Agent 框架的威胁模型下风险极低。

**File Location:** `framework/agent_framework/tools/builtin/file_tools.py:20-21,39-40`

**Impact:** 在单用户本地运行场景下无实际风险。如果未来支持多用户并发或不受信任的文件系统操作，TOCTOU 可能被利用。

**Fix Suggestion:** 当前实现足够安全。如需加强，可在 `safe_path` 后立即使用 `os.open(O_NOFOLLOW)` 打开文件描述符，在 fd 上操作而非路径。但这会增加实现复杂度，当前阶段不推荐。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-SEC-15: MCP _reject_sensitive_env_keys 覆盖不完整

**Description:** `mcp/config.py:19-27` 中 `_BLOCKED_ENV_PATTERNS` 包含 7 个模式：`api_key`, `token`, `secret`, `password`, `credential`, `private_key`, `access_key`。validator 使用 `any(pattern in lowered for pattern in _BLOCKED_ENV_PATTERNS)` 做子串匹配。这意味着 `MY_TOKEN`、`API_KEY_V2` 等变体能被捕获。但以下模式未被覆盖：`auth`（如 `AUTHORIZATION`）、`session`（如 `SESSION_ID`）、`cookie`（如 `COOKIE_TOKEN`）、`bearer`（如 `BEARER_AUTH`）、`refresh`（如 `REFRESH_TOKEN`）、`jwt`（如 `JWT_SECRET`）。

**File Location:** `framework/agent_framework/tools/mcp/config.py:19-27`

**Impact:** MCP server 配置可以注入 `AUTHORIZATION`、`SESSION_ID`、`COOKIE` 等敏感环境变量，绕过当前的环境变量过滤。虽然 MCP server 本身是本地子进程，但如果恶意 MCP 配置被加载，敏感凭据可能泄露给第三方 MCP server 进程。

**Fix Suggestion:** 扩展 `_BLOCKED_ENV_PATTERNS` 增加 `auth`、`session`、`cookie`、`bearer`、`refresh`、`jwt` 模式。或改用白名单机制：只允许配置中以 `MCP_` 前缀开头的环境变量。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-SEC-16: MCP transport.py 直接合并 env 继承全部系统环境变量

**Description:** `mcp/transport.py:57` 中 `StdioTransport.connect()` 使用 `env = {**os.environ, **(self._env or {})}` 构建子进程环境变量。这意味着 MCP server 子进程继承了完整的系统环境——包括当前进程中所有环境变量（如 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`DATABASE_URL` 等）。虽然 `_reject_sensitive_env_keys` 会过滤用户在 config 中显式设置的敏感 key，但子进程自动继承的环境变量不受此限制。

**File Location:** `framework/agent_framework/tools/mcp/transport.py:57`

**Impact:** 如果安装了不受信任的 MCP server（如社区提供的第三方 server），该 server 的子进程可以通过读取环境变量获取宿主进程的所有 API key 和凭据。

**Fix Suggestion:** 改为白名单机制：子进程只继承必要的环境变量（如 `PATH`、`HOME`、`TEMP`），加上 MCP config 中显式声明的 `env` 字段。或至少在文档中明确说明 MCP server 子进程继承全部环境变量的安全影响。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-ARCH-08: compactor.py 压缩操作每次额外消耗一次 LLM API 调用

**Description:** `tools/context/compactor.py:126-156` 中 `_generate_summary` 每次压缩都会调用 `adapter.complete()` 发起一次完整的 LLM API 请求。这个调用使用 `max_tokens=8000`，每次消耗的 token 数等于序列化后的旧消息 + 8000 output token。对于长对话，序列化输入可能非常大。

**File Location:** `framework/agent_framework/tools/context/compactor.py:126-156`

**Impact:** (1) 每次 compaction 的 API 成本可能高于被节省的 token 成本（如果旧消息不多，摘要本身的开销可能大于节省的上下文空间）。(2) 增加了请求延迟——compaction 期间 Agent 循环被阻塞等待 LLM 响应。(3) 如果 LLM 调用失败（如 rate limit），compaction 失败且没有 fallback。

**Fix Suggestion:** (1) 添加最小压缩阈值：只有当旧消息超过一定量时才触发 LLM 摘要（否则直接丢弃旧消息或使用简单截断）。(2) 为 `_generate_summary` 添加 try-except，LLM 调用失败时 fallback 到简单截断（只保留每条消息的前 N 个字符）。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-09: search_tools.py 模块级可变全局状态（_client 单例 + _semaphore）

**Description:** `tools/builtin/search_tools.py` 在模块级定义了 `_client: AsyncTavilyClient | None = None`（行 16）和 `_semaphore: asyncio.Semaphore = asyncio.Semaphore(5)`（行 13）。(1) `_client` 使用 `global` 赋值在 `_get_client()` 中实现懒加载单例——模块级全局可变状态，多 Agent 实例共享同一个 client。(2) `_semaphore` 在模块导入时创建，但 `asyncio.Semaphore` 绑定到创建时的事件循环——如果在不同的 asyncio 事件循环中使用（如测试场景），semaphore 可能不工作。(3) `reset_client()` 通过 `global` 重置——如果两个 Agent 同时调用 `reset_client()` 和 `_get_client()`，存在竞态条件。

**File Location:** `framework/agent_framework/tools/builtin/search_tools.py:13,16,21-27,30-33`

**Impact:** (1) 全局单例导致测试难以隔离——一个测试重置 client 会影响其他测试。(2) 跨事件循环使用时 semaphore 可能抛 `RuntimeError: Task attached to a different loop`。(3) 多 Agent 实例共享同一个并发限制（5），而非每个 Agent 独立控制。

**Fix Suggestion:** 将 `_client` 和 `_semaphore` 移入类中（如 `SearchToolProvider`），通过依赖注入传入 ToolSpec handler。消除模块级可变状态。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-07: ToolValidator 不验证 unknown 参数和 enum 约束

**Description:** `tools/validator.py` 的 `validate` 方法只检查两项：(1) required 字段是否存在（行 26-31），(2) 已提供参数的 type 是否匹配（行 34-49）。但它不验证：(1) 调用方传入的参数是否在 schema 的 properties 中定义（unknown 参数被静默忽略）。(2) enum 约束——`memory_tools.py` 的 `event_type` 参数定义了 `enum: ["决策", "偏好", "错误", "约定", "进展"]`，但 validator 不检查传入值是否在 enum 列表中。enum 验证由 handler 自己做（如 `handle_memory_write` 行 31 的 `EventType(raw_type)` 会抛 ValueError）。

**File Location:** `framework/agent_framework/tools/validator.py:21-51`

**Impact:** (1) LLM 生成的 tool call 可能包含拼写错误的参数名，validator 不会报错，handler 收到缺少必要参数的调用。(2) enum 约束不在 validator 层执行意味着每个 handler 都要自行验证 enum 值，违反 DRY 原则。

**Fix Suggestion:** 在 validator 中添加 enum 检查：`if "enum" in prop_schema and value not in prop_schema["enum"]: return error`。对于 unknown 参数，至少记录 warning 或根据 strict 模式决定是否拒绝。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-08: ToolUseContext.extra 的 dict[str, Any] 无类型安全

**Description:** `tools/types.py:57` 中 `ToolUseContext.extra: dict[str, Any] = {}` 是一个完全无类型的字典。各个 handler 通过字符串 key 访问特定值（如 `ctx.extra.get("memory_dir")`、`ctx.extra.get("memory_store")`、`ctx.extra.get("planning_session")`），但没有任何类型检查或文档说明合法的 key 集合。如果 key 拼写错误（如 `"memoryDire"` 代替 `"memory_dir"`），运行时只会得到 `None`，不会报错。

**File Location:** `framework/agent_framework/tools/types.py:57`

**Impact:** handler 和调用方之间的接口契约完全靠约定维持，没有编译时检查。拼写错误的 key 导致 handler 静默进入 fallback 路径或返回错误。

**Fix Suggestion:** 将 `extra` 改为结构化的 TypedDict 或 Pydantic model，明确定义所有合法 key 及其类型。如 `class ToolExtra(TypedDict, total=False): memory_dir: str; memory_store: MemoryStore; planning_session: PlanningSession`。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-09: McpManager._register_tools 注册无 handler 的 ToolSpec

**Description:** `mcp/config.py:109-124` 中 `_register_tools` 为 MCP 工具创建 ToolSpec 但不设置 `handler`（默认为 `None`）。这些 ToolSpec 注册到 registry 后，如果通过 `_dispatch_builtin` 调用（而非 `_dispatch_mcp`），`ToolExecutor.execute()` 会在行 25-29 返回"工具不可执行（无 handler）"。虽然 dispatch 通过 `name.startswith("mcp__")` 路由到 `_dispatch_mcp`，但如果有人直接调用 `registry.get("mcp__xxx")` 然后通过 executor 执行，会得到不明确的错误。

**File Location:** `framework/agent_framework/tools/mcp/config.py:109-124`

**Impact:** MCP 工具的 ToolSpec 与 builtin 工具的 ToolSpec 行为不一致——前者无 handler（依赖路由层分派），后者有 handler。这违反了 ToolSpec 的隐含契约（有 handler 就能执行）。

**Fix Suggestion:** (1) 为 MCP 工具的 ToolSpec 设置一个 lambda handler 转发到 `_dispatch_mcp`，使 ToolSpec 自包含。(2) 或在 ToolSpec 中添加 `source: Literal["builtin", "mcp", "agent"]` 字段，明确标识工具来源。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-SEC-17: MCP config.py shutdown 中 try-except-pass 静默吞异常

**Description:** `mcp/config.py:95-102` 中 `McpManager.shutdown()` 的 except 分支使用 `except Exception: pass`，静默跳过单个 client 关闭失败。ruff S110 已标记此模式。在并发场景下，如果多个 MCP client 关闭失败，全部被静默忽略，可能导致子进程泄漏。

**File Location:** `framework/agent_framework/tools/mcp/config.py:97-101`

**Impact:** MCP server 子进程关闭失败时，进程可能继续运行（孤儿进程），占用资源且无法追踪。

**Fix Suggestion:** 添加 `logger.debug` 记录关闭失败的原因和 server 名称。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-DEAD-12: memory_tools.py 导入 datetime 但可使用 dataclass 替代

**Description:** `tools/builtin/memory_tools.py:7` 导入了 `datetime`，但 `datetime.now()` 仅用于获取当前时间戳传给 `EpisodicLogManager.append()`。该模块本身不需要 datetime 的复杂功能，但这是合理的标准库使用，不算真正的死代码。

**File Location:** `framework/agent_framework/tools/builtin/memory_tools.py:7`

**Impact:** 无实际影响。

**Fix Suggestion:** 无需修改。

**Priority:** MEDIUM
**Related:** FRMW-01 (死代码检测)

---

### LOW

#### FRMW-ARCH-10: ToolDegrader 降级到 builtin 但不支持降级到 MCP 工具

**Description:** `tools/degrader.py` 的 `_fallbacks` 映射只支持 `tool_name -> fallback_tool_name` 的简单映射。在 `ToolRouter.dispatch()` 行 113-117 中，降级时固定调用 `_dispatch_builtin`（行 114），这意味着降级目标只能是 builtin 工具。如果需要降级到 MCP 工具（如本地搜索工具失败时降级到 MCP 搜索服务），当前实现不支持。

**File Location:** `framework/agent_framework/tools/degrader.py`, `framework/agent_framework/tools/router.py:113-117`

**Impact:** 降级策略的范围受限于 builtin 工具。在当前只有 6 个 builtin 工具的场景下，实际影响很小。

**Fix Suggestion:** 降级时使用 `dispatch(active_call, ctx)` 替代 `_dispatch_builtin`，让降级工具也能走完整的路由逻辑（包括 MCP 路由）。需要注意防止降级工具再次失败导致的无限递归。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-11: registry.py subset() 静默跳过不存在的工具名

**Description:** `tools/registry.py:29-35` 中 `subset(names)` 方法对传入的每个 name 调用 `self.get(name)`，如果返回 None 则静默跳过。调用方无法知道请求的工具中哪些不存在。

**File Location:** `framework/agent_framework/tools/registry.py:29-35`

**Impact:** 如果调用方期望的工具列表中有拼写错误，subset 会静默返回不完整的子集，不会报错。可能导致运行时缺少必要工具。

**Fix Suggestion:** 添加 `strict` 参数：`subset(names, strict=False)` — 当 `strict=True` 时，遇到不存在的 name 抛出 `KeyError`。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-12: compactor.py _serialize_for_summary 只提取 TextBlock

**Description:** `tools/context/compactor.py:103-123` 中 `_serialize_for_summary` 对 `UserMessage` 和 `AssistantMessage` 只提取 `TextBlock`（行 112-114, 116-118），忽略了 `ToolUseBlock`、`ToolResultBlock` 等 content block。这意味着摘要 LLM 看不到工具调用和结果，只看到纯文本部分。

**File Location:** `framework/agent_framework/tools/context/compactor.py:112-118`

**Impact:** 如果对话中有大量工具调用（如 Agent 执行了多步 plan），摘要 LLM 只能看到 `[Assistant] ` 后面没有任何工具调用内容。摘要质量会下降——丢失了"Agent 做了什么"的关键信息。

**Fix Suggestion:** 为 `ToolUseBlock` 提取 `name + input` 摘要，为 `ToolResultBlock` 提取 `content[:200]` 摘要。保持序列化简洁但信息完整。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-13: ToolRouter.dispatch 中 PreHook 和 PostHook 使用不同的 name 变量

**Description:** `router.py` 行 62 定义 `name = call.name`，行 79 定义 `active_call = call`。PreHook 阶段可能通过 `hr.updated_input` 创建新的 `active_call`（行 94-98），但 PostHook 阶段（行 138-155）使用的 `name` 仍是原始的 `call.name`，而非 `active_call.name`。虽然当前 PreHook 不修改 tool name（只修改 arguments），但这是一个潜在的一致性问题。

**File Location:** `framework/agent_framework/tools/router.py:62,79,138`

**Impact:** 当前无实际影响——PreHook 只修改 `updated_input`（参数），不修改工具名。但如果未来 PreHook 支持重定向工具名（将调用从工具 A 改到工具 B），PostHook 会使用错误的工具名。

**Fix Suggestion:** 在创建 `active_call` 后更新 `name = active_call.name`，或在 PostHook 中统一使用 `active_call.name`。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-10: ToolResult.metadata 默认空 dict 共享引用问题

**Description:** `tools/types.py:25` 中 `ToolResult.metadata: dict[str, Any] = {}`。由于 Pydantic BaseModel 的默认值在类定义时求值，如果多个 ToolResult 实例共享同一个默认 dict，修改一个实例的 metadata 可能影响其他实例。不过 Pydantic v2 的 `model_config` 默认行为会为每个实例创建独立的 dict，所以实际不会触发此问题。

**File Location:** `framework/agent_framework/tools/types.py:25`

**Impact:** Pydantic v2 已正确处理此场景，无实际影响。但如果迁移到其他框架或手写 dataclass，可能出现共享引用问题。

**Fix Suggestion:** 可使用 `Field(default_factory=dict)` 替代 `= {}`，更明确地表达意图。但当前 Pydantic 行为正确，非必要修改。

**Priority:** LOW
**Related:** FRMW-02 (逻辑漏洞)

---

## agents/

逐文件审查范围：6 个源文件，~1135 行（agent_loop.py 469 行、reflection.py 223 行、plan_and_solve.py 201 行、sub_agent.py 93 行、config.py 104 行、base.py 24 行）。
模块职责：ReAct Agent 主循环、反思 Agent、规划-求解 Agent、子 Agent、Agent 配置化。

### CRITICAL

*(none found)*

### HIGH

#### FRMW-SEC-08: agent_loop.py 中 logger 未定义导致运行时 NameError

**Description:** `agent_loop.py:288` 使用 `logger.debug("语义记忆提取失败（best-effort）", exc_info=True)` 但文件中没有 `import logging` 和 `logging.getLogger(__name__)` 声明。当 `SemanticExtractor.extract_from_messages()` 抛出异常时，except 分支（行 287-288）触发，会先抛出 `NameError: name 'logger' is not defined`，掩盖原始异常。ruff F821 已检测此问题。

**File Location:** `framework/agent_framework/agents/agent_loop.py:288`

**Impact:** Memory flush 的语义记忆提取失败时，原始异常被 NameError 掩盖。外层 `except Exception`（行 291）捕获的是 NameError 而非原始异常，`compact_failures` 计数器递增但无法记录真实的失败原因。连续 3 次后 compaction 被 circuit breaker 禁用，用户无感知。

**Fix Suggestion:** 在文件顶部（`import asyncio` 后）添加：
```python
import logging
logger = logging.getLogger(__name__)
```

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-DEAD-04: agent_loop.py 导入未使用的 dataclasses.field

**Description:** `agent_loop.py:9` 导入 `from dataclasses import dataclass, field`，但 `field` 在整个文件中从未使用。文件中唯一的 `@dataclass` 是 `LoopEvent`（行 56），它使用 `plan: PlanSnapshot | None = None` 作为默认值，不需要 `field()`。

**File Location:** `framework/agent_framework/agents/agent_loop.py:9`

**Impact:** 代码噪音。

**Fix Suggestion:** 改为 `from dataclasses import dataclass`。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-DEAD-05: config.py、sub_agent.py 导入未使用的 Agent 类

**Description:** `agents/config.py:9` 和 `agents/sub_agent.py:6` 都导入了 `agent_framework.agents.base.Agent` 但未使用。`config.py` 中的 `agent_from_config()` 返回 `AgentLoop`（非 `Agent`），类型注解也没用 `Agent`。`sub_agent.py` 中的 `run_subagent()` 没有返回类型注解引用 `Agent`。`base.py` 中 `Agent` 是一个 ABC（24 行，含 `AgentEvent` dataclass 和 `Agent` 抽象类），不是空文件——但这两个文件确实没使用它。

**File Location:** `framework/agent_framework/agents/config.py:9`, `framework/agent_framework/agents/sub_agent.py:6`

**Impact:** 增加了不必要的 coupling 到 `base.py`。如果 `Agent` ABC 将来被移除或重命名，这两个文件的 import 会失败。

**Fix Suggestion:** 移除 `Agent` 的 import。`config.py` 中 `agent_from_config` 返回 `AgentLoop` 已足够。`sub_agent.py` 不需要类型注解。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-DEAD-06: reflection.py 导入未使用的 typing.Any

**Description:** `agents/reflection.py:9` 导入了 `from typing import Any, AsyncGenerator`，但 `Any` 在文件中从未使用。文件中所有类型注解都使用了具体类型（`str`、`dict[str, int]`、`ReflectionVerdict` 等）。

**File Location:** `framework/agent_framework/agents/reflection.py:9`

**Impact:** 代码噪音。

**Fix Suggestion:** 改为 `from typing import AsyncGenerator`。

**Priority:** HIGH
**Related:** FRMW-01 (死代码检测)

---

#### FRMW-ARCH-14: AgentLoop.__init__ 19 个参数，构造器过于复杂

**Description:** `AgentLoop.__init__` 接受 19 个参数（行 69-91），是全框架参数最多的构造器（PLR0913 排名第一）。参数分为多个类别：(1) 核心依赖（adapter, model, router, ctx），(2) 执行控制（max_steps, system_prompt），(3) 计划管理（drift_warn, drift_abort），(4) 上下文压缩（compact_adapter, compact_keep_turns, compact_trigger_pct），(5) 记忆集成（memory_flush_enabled, semantic_extractor），(6) 工具/技能扩展（skill_dirs, hook_manager, task_runner, enable_subagent, team_manager），(7) 权限（profile）。构造器体（行 92-164）长达 73 行，包含大量条件初始化逻辑。

**File Location:** `framework/agent_framework/agents/agent_loop.py:69-164`

**Impact:** (1) 构造器难以正确调用——19 个关键字参数中哪些必填、哪些有默认值、哪些互相关联，需要阅读整个签名才能理解。(2) 构造器承担了过多初始化逻辑：skill 注册、memory store 创建、sub-agent spec 注册、plan instruction 注入等。(3) 测试时需要构造大量 mock 依赖。

**Fix Suggestion:** 引入配置对象模式，将相关参数分组：
```python
@dataclass
class AgentLoopConfig:
    max_steps: int = 10
    system_prompt: str = "..."
    compact: CompactConfig | None = None
    memory: MemoryConfig | None = None
    skills: SkillConfig | None = None
    ...
```
构造器只接受核心依赖（adapter, model, router, ctx）+ config 对象。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-15: AgentLoop.run() C901 复杂度 30，单方法 175 行

**Description:** `AgentLoop.run()` 方法（行 295-469）是全框架最复杂的函数（C901=30，行数 175）。方法包含：(1) 消息初始化分支（resume vs fresh），(2) SessionStart hook，(3) plan 注入，(4) 主循环（最多 max_steps 轮），循环内包含：(4a) task notification drain，(4b) team notification drain，(4c) plan context 注入，(4d) context compaction + LLM 调用，(4e) 5 个 stop_reason 分支（END_TURN, MAX_TOKENS, STOP_SEQUENCE, TOOL_USE, fallback），(4f) tool execution + drift detection。

**File Location:** `framework/agent_framework/agents/agent_loop.py:295-469`

**Impact:** (1) 难以理解完整执行流程——阅读者需要跟踪 5 层嵌套的 if/for。(2) 难以单独测试某个 stop_reason 分支。(3) 添加新的 stop_reason 或集成新的子系统（如新的 hook 点）需要修改这个巨型方法。(4) 多个子系统（task_runner, team_manager, planning）的通知 drain 逻辑内联在主循环中，职责不清。

**Fix Suggestion:** 拆分为多个私有方法：
- `_init_messages(user_message, resume)` — 消息初始化
- `_drain_notifications()` — 统一的通知 drain（task + team）
- `_inject_plan_context()` — 计划上下文注入
- `_handle_stop_reason(result, step)` — stop_reason 分流
- `_execute_tool_calls(result, step)` — 工具调用执行 + drift
主循环 `run()` 只保留 `for step in range(...)` 和上述方法的编排。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

### MEDIUM

#### FRMW-LOGIC-11: AgentLoop.run() 中 plan context 注入使用 pop(i) 反向遍历会消息列表

**Description:** `agent_loop.py:367-373` 中，plan context 注入逻辑在 `_messages` 列表上做反向遍历查找旧 plan 消息，找到后用 `pop(i)` 删除。这个操作在 `for step in range(1, max_steps + 1)` 循环内，每轮都执行。(1) 反向遍历搜索是 O(n) 操作，长对话中每轮都遍历整个消息列表。(2) `pop(i)` 修改了正在迭代的列表，虽然这里是 `range` 而非直接遍历列表，但 `break` 后只删除一个，逻辑正确。(3) 依赖 `self._planning.is_plan_context_text()` 做内容匹配——如果用户消息恰好包含计划文本模式，会被误删。

**File Location:** `framework/agent_framework/agents/agent_loop.py:367-373`

**Impact:** (1) 每轮循环遍历整个消息列表查找 plan context，性能随对话长度线性下降。(2) 字符串匹配可能误删用户消息——虽然 `is_plan_context_text` 检查特定标记（如 `<plan-context>`），但如果标记出现在用户原始输入中，消息会被误删。

**Fix Suggestion:** (1) 使用独立变量追踪 plan context 消息的索引，避免每轮遍历。(2) 为 plan context 消息添加唯一标记（如 UUID），避免内容匹配。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-12: AgentLoop._maybe_compact 中 flush 和 compact 并行执行但异常处理不一致

**Description:** `agent_loop.py:262-269` 中，当 `_flush_extractor` 存在时，使用 `asyncio.gather(flush_coro, compact(...), return_exceptions=True)` 并行执行 flush 和 compact。`return_exceptions=True` 意味着 flush 的异常也会被包装为返回值而非抛出。(1) 代码只检查 `result`（compact 结果）是否为 Exception，完全不处理 flush 的异常——如果 flush 失败，返回的 `_` 被忽略。(2) 如果 compact 成功但 flush 抛出异常，`_compact_failures` 被重置为 0（行 274），掩盖了 flush 的问题。

**File Location:** `framework/agent_framework/agents/agent_loop.py:262-274`

**Impact:** flush 失败被完全静默——记忆不会被持久化，但不会影响 compaction。这可能是有意设计（best-effort flush），但缺乏日志记录使得问题难以追踪。

**Fix Suggestion:** 检查 flush 结果并记录日志：
```python
flush_result, compact_result = await asyncio.gather(...)
if isinstance(flush_result, Exception):
    logger.warning("Memory flush 失败（best-effort）: %s", flush_result)
```

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-13: ReflectionAgent 循环次数 = max_improvement_rounds + 1，语义含混

**Description:** `reflection.py:117` 中循环条件为 `range(self.max_improvement_rounds + 1)`，总执行次数 = max_improvement_rounds + 1（默认 3 次：1 次初始执行 + 2 次改进）。但 `max_improvement_rounds` 的命名暗示"最大改进次数"，实际行为是"初始执行 + N 次改进"——总 LLM 调用次数 = (N+1) * (1 次执行 + 1 次评估) = 2*(N+1)。默认配置下 6 次 LLM 调用。

**File Location:** `framework/agent_framework/agents/reflection.py:117`

**Impact:** 命名与行为不一致可能导致调用方误解总成本。`max_improvement_rounds=2` 实际产生 6 次 LLM 调用（3 次执行 + 3 次评估），不是 4 次。

**Fix Suggestion:** 重命名为 `max_total_rounds` 或在 docstring 中明确说明总轮次数。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-ARCH-16: ReflectionAgent 和 PlanAndSolveAgent 都内部创建新 AgentLoop 实例

**Description:** `ReflectionAgent._collect_loop_output`（行 175-198）和 `PlanAndSolveAgent._collect_loop_output`（行 160-173）都在内部创建新的 `AgentLoop` 实例。这意味着：(1) 每次创建的 AgentLoop 不继承父 AgentLoop 的 memory、planning、skill、hook 等状态——这些新实例使用默认 system_prompt，没有记忆索引，没有技能注册。(2) 每次执行都创建新的 `_messages` 列表，不复用对话历史。(3) `PlanAndSolveAgent` 对每个 plan step 创建独立的 AgentLoop（行 84-90），step 之间通过 `step_outputs` 字符串列表传递结果，丢失了完整的消息上下文。

**File Location:** `framework/agent_framework/agents/reflection.py:177-183`, `framework/agent_framework/agents/plan_and_solve.py:84-90`

**Impact:** (1) 反思 Agent 的改进轮次从零开始，不继承前一轮的工具调用结果。LLM 无法看到之前调用过的工具返回。(2) Plan-and-Solve 的每个 step 是独立上下文，前序步骤的完整对话历史被压缩为文本摘要（`step_outputs`），信息损失严重。(3) 两个 Agent 类型都无法利用父 AgentLoop 的 compact、memory flush、semantic extraction 等高级功能。

**Fix Suggestion:** 为 ReflectionAgent 和 PlanAndSolveAgent 添加配置参数，允许传入共享的 AgentLoop 或至少继承关键的 context 状态（如 system_prompt、skill_registry、hook_manager）。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-17: PlanAndSolveAgent._is_step_failed 的失败检测过于粗糙

**Description:** `plan_and_solve.py:152-158` 中 `_is_step_failed` 仅检查两个条件：(1) 输出为空或空白，(2) 输出包含 `"[子代理错误]"` 字符串。这意味着只有完全无输出或显式错误标记才被识别为失败。如果 Agent 产生了看起来合理但实际错误的输出（如代码有 bug、推理有误），`_is_step_failed` 不会检测到，plan 会继续执行后续步骤。

**File Location:** `framework/agent_framework/agents/plan_and_solve.py:152-158`

**Impact:** 计划执行的质量保障完全依赖最终结果的审查，中间步骤的错误不会被捕获。如果中间步骤产出了错误但非空的结果，后续步骤基于错误信息继续执行，错误会累积。

**Fix Suggestion:** (1) 添加更多失败模式检测：包含 `"error"` 或 `"failed"` 等关键词（但需要避免误报）。(2) 或引入 LLM-as-judge 在每个 step 后评估输出质量（类似 ReflectionAgent 的 `_reflect`）。(3) 当前的简单检测作为 minimum viable 方案是可接受的，但应在文档中明确说明限制。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-14: PlanAndSolveAgent replan 后重置 i=0 但不清理已完成的 plan items

**Description:** `plan_and_solve.py:104-116` 中，当 step 失败触发 replan 时（行 114-116），`step_outputs = []` 和 `i = 0` 重置了执行进度，但 `self._planning.create_from_items(new_plan, "llm_generated")` 会用新的 plan items 替换旧的。然而 `self._planning` 对象被创建时 `allow_replan=False`（行 49-53），这限制了 planning session 的 replan 能力。但这里 `create_from_items` 直接替换了整个 plan，绕过了 `allow_replan` 的限制。

**File Location:** `framework/agent_framework/agents/plan_and_solve.py:49-53,104-116`

**Impact:** (1) replan 后所有已完成的 step 输出被丢弃，即使某些步骤的输出是正确的。(2) `allow_replan=False` 与实际行为不一致——PlanAndSolveAgent 确实支持 replan（通过直接调用 `create_from_items`），但 PlanningSession 的 `allow_replan=False` 可能限制了其他方法的行为。(3) 如果新计划生成失败（行 110-117 的 `if new_plan:` 不成立），继续使用旧计划但不重置 `i`，可能导致跳过后续步骤。

**Fix Suggestion:** replan 时应保留已完成的 step 输出（或至少提供选项）。`PlanningSession` 的 `allow_replan` 参数应反映实际行为。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-SEC-18: run_subagent 共享 ToolUseContext 导致状态泄漏

**Description:** `sub_agent.py:38-46` 中 `run_subagent` 直接使用传入的 `ctx: ToolUseContext` 创建子 AgentLoop。这意味着子 agent 和父 agent 共享同一个 `ctx.extra`、`ctx.app_state`、`ctx.message_history` 字典。如果子 agent 修改了 `ctx.extra`（如添加/修改 key），修改会影响父 agent 的后续执行。

**File Location:** `framework/agent_framework/agents/sub_agent.py:39-46`

**Impact:** 子 agent 的副作用会泄漏到父 agent。例如，子 agent 可能修改 `ctx.extra["memory_dir"]` 或 `ctx.extra["planning_session"]`，导致父 agent 行为异常。当前 `create_run_subagent_spec` 的 handler（行 66-75）直接传递 `ctx` 给子 agent，没有隔离。

**Fix Suggestion:** 在 `run_subagent` 中创建 `ctx` 的浅拷贝：`child_ctx = ctx.model_copy(update={"extra": {**ctx.extra}})`，确保子 agent 的 `extra` 修改不影响父 agent。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-DEAD-13: agent_loop.py 导入 Path 但 skill_dirs 参数类型已内联

**Description:** `agent_loop.py:10` 导入 `from pathlib import Path`，在文件中用于 `skill_dirs: list[Path] | None`（行 86）和 `Path(memory_dir)`（行 145, 159, 281）。`Path` 实际被使用，这个 import 不是死代码——CONCERNS.md 中记录的 "Path import 缺失" 问题在当前代码中已不存在（已正常导入）。

**File Location:** `framework/agent_framework/agents/agent_loop.py:10`

**Impact:** 无——Path 导入正常且被使用。CONCERNS.md 中的 "Path import 缺失" bug 已被修复。

**Fix Suggestion:** 无需修改。

**Priority:** MEDIUM
**Related:** FRMW-01 (死代码检测)

---

### LOW

#### FRMW-ARCH-18: Agent ABC 的 run() 返回 AsyncGenerator[AgentEvent, None] 但无类型别名

**Description:** `base.py:23` 中 `Agent.run()` 的返回类型为 `AsyncGenerator[AgentEvent, None]`，这是一个复杂的泛型类型注解。项目中所有 Agent 子类都重复这个注解。可以定义 `AgentRunResult = AsyncGenerator[AgentEvent, None]` 类型别名简化签名。

**File Location:** `framework/agent_framework/agents/base.py:23`

**Impact:** 轻微的代码可读性问题。

**Fix Suggestion:** 在 base.py 中定义类型别名。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-19: ReflectionAgent._collect_loop_output 手动解析 content blocks

**Description:** `reflection.py:186-197` 中 `_collect_loop_output` 手动遍历 `event.data.get("content", [])` 查找 text block。这段解析逻辑与 `agent_loop.py` 的 `_extract_text` 重复，且使用 `dict` 操作（`block.get("type")`）而非类型化的 ContentBlock 对象。这是因为 LoopEvent.data 中的 content 被 `_serialize_content` 序列化为 dict。

**File Location:** `framework/agent_framework/agents/reflection.py:186-197`

**Impact:** 代码重复，且使用 dict 而非类型化对象降低了类型安全性。

**Fix Suggestion:** 在 LoopEvent 或 AgentEvent 中添加 `extract_text()` 辅助方法，封装 content block 遍历逻辑。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-15: config.py 中 parse_agent_config 的 tools 参数解析脆弱

**Description:** `config.py:53` 中 `tools_raw = meta.get("tools", "")` 然后 `tools_raw.split(",")` 解析工具列表。这意味着工具名不能包含逗号（否则被错误分割），且无法处理引号包裹的工具名。此外 `tools_raw` 为空字符串时 `[t.strip() for t in "".split(",") if t.strip()]` 返回空列表而非 `None`——只有 `if not tools_raw` 时才返回 None，但这检查的是原始字符串，如果 frontmatter 中 `tools: ""` 则 `tools_raw == ""` 为真，返回 None，行为正确。

**File Location:** `framework/agent_framework/agents/config.py:53`

**Impact:** 工具名中包含逗号会被错误分割。当前所有内置工具名都不含逗号，无实际影响。

**Fix Suggestion:** 如果需要支持复杂工具名，改用 YAML 列表语法（`tools: [tool1, tool2]`），`parse_frontmatter` 已支持列表解析。

**Priority:** LOW
**Related:** FRMW-02 (逻辑漏洞)

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

逐文件审查范围：9 个源文件，~944 行（store.py 111 行、log_manager.py 80 行、index_manager.py 112 行、semantic_writer.py 134 行、semantic_extractor.py 118 行、retriever.py 111 行、search.py 50 行、flush.py 102 行、frontmatter.py 56 行、types.py 43 行）。
模块职责：记忆持久化（情景日志 + 语义记忆）、LLM 评分召回、对话 flush 提取、frontmatter 解析。

### CRITICAL

*(none found)*

### HIGH

#### FRMW-ARCH-20: memory/ 全模块使用同步 I/O 阻塞事件循环

**Description:** memory/ 模块的所有文件 I/O 操作均使用同步调用：`Path.read_text()`、`Path.write_text()`、`open() + f.write()`。这些方法在 async 框架的上下文中被调用（如 `MemoryStore.search()` 是 `async def`，内部调用 `self._search_episodic()` 使用同步 `EpisodicLogManager.read_log()`）。以下关键路径全部同步阻塞：

- `store.py:80-94` — `_search_episodic()` 遍历日期文件并 `read_log()` 读取全文
- `log_manager.py:44-45` — `append()` 使用 `open(log_path, "a")` 同步追加
- `log_manager.py:52` — `read_log()` 使用 `log_path.read_text()` 同步读取
- `log_manager.py:60-61` — `write_raw()` 使用 `open()` 同步写入
- `index_manager.py:52` — `_atomic_write()` 虽然使用 rename 模式保证原子性，但写入本身是同步的
- `index_manager.py:99` — `remove()` 使用 `read_text()` 同步读取
- `semantic_writer.py:106` — `_create()` 使用 `path.write_text()` 同步写入
- `semantic_writer.py:126` — `_merge()` 使用 `read_text()` + `open("a")` 同步读写
- `retriever.py:45` — `_scan_candidates()` 使用 `f.read_text()` 同步扫描所有 .md 文件
- `retriever.py:107` — 读取选中记忆文件内容使用 `fpath.read_text()` 同步读取

**File Location:** `framework/agent_framework/memory/` 全模块

**Impact:** 在 async Agent 框架中，同步文件 I/O 阻塞事件循环。`_search_episodic()` 遍历所有日期日志并逐个 `read_text()`，当日志文件增多时阻塞时间线性增长。`_scan_candidates()` 扫描所有 .md 文件读取 frontmatter，文件数多时同样阻塞。在并发 agent 场景下，一个 agent 的记忆搜索会阻塞其他 agent 的执行。

**Fix Suggestion:** (1) 使用 `aiofiles` 替换所有 `open()`/`read_text()`/`write_text()`。(2) 或使用 `asyncio.to_thread()` 包装同步 I/O 调用。(3) `log_manager.py` 已在文档注释（行 3-4）中说明此限制，但未给出迁移计划。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-21: retriever._scan_candidates 读取全部文件内容只为提取 frontmatter

**Description:** `LLMScoringRetriever._scan_candidates()`（retriever.py:37-53）对每个 .md 文件调用 `f.read_text(encoding="utf-8")` 读取完整文件内容，然后只调用 `parse_frontmatter(content)` 提取头部的几行元数据。当记忆文件较大（如含多次 merge 追加的语义记忆）时，读取完整文件只为提取前几行 frontmatter 是显著的性能浪费。

**File Location:** `framework/agent_framework/memory/retriever.py:45`

**Impact:** 50 个记忆文件中，如果平均每个 5KB，每次搜索需要读取 250KB 并解析，但实际只需要每个文件的前 10-20 行。在 `max_candidates=50` 限制下，影响可控但不必要。

**Fix Suggestion:** 只读取文件头部（前 512 字节或到第二个 `---` 行为止），不读取完整内容。或维护一个 frontmatter 缓存，在文件写入时更新。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

### MEDIUM

#### FRMW-SEC-10: semantic_writer.py 使用 sha1 哈希生成文件名

**Description:** `memory/semantic_writer.py:47` 使用 `hashlib.sha1()` 从语义记忆名称生成文件名 slug。ruff S324 标记此为不安全哈希。但此场景仅用于生成唯一文件名，不涉及安全验证。

**File Location:** `framework/agent_framework/memory/semantic_writer.py:47`

**Impact:** 无实际安全风险。sha1 仅用于生成确定性文件名，不用于认证或完整性验证。

**Fix Suggestion:** 可替换为 `hashlib.sha256()` 或 `hashlib.md5()` 消除 S324 告警，但不影响正确性。也可添加 `# noqa: S324`。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-LOGIC-16: store._search_episodic 对完整日志内容做 re.split 性能问题

**Description:** `MemoryStore._search_episodic()`（store.py:83）对每个日期日志的完整内容使用 `re.split(r"(?=^## )", content, flags=re.MULTILINE)` 进行分割。当日志文件积累大量条目时（数百条事件），每次搜索都需要对所有日期日志做正则分割和子串匹配。

**File Location:** `framework/agent_framework/memory/store.py:83-94`

**Impact:** 搜索性能随日志数量线性下降。假设 30 天日志、每天 20 条事件，每次搜索需要处理 600 条事件的正则分割和文本匹配。

**Fix Suggestion:** 为情景记忆建立倒排索引或关键词缓存，避免每次搜索全量扫描。短期可接受，长期需要索引化。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-17: flush.py flush() 方法错误恢复能力不足

**Description:** `FlushExtractor.flush()`（flush.py:86-101）在 LLM 提取事件后直接调用 `log_manager.write_raw()` 写入。如果 `write_raw()` 因磁盘满或权限错误失败，异常会向上传播，但之前 LLM 调用已消耗的 token 不会被缓存或重试。此外，`flush()` 返回 `bool` 表示是否有事件写入，但调用方（`AgentLoop._maybe_compact`）不检查这个返回值——即使 flush 失败，compaction 仍会继续。

**File Location:** `framework/agent_framework/memory/flush.py:86-101`

**Impact:** flush 失败时事件丢失，但不会影响 compaction 本身。LLM 提取的事件是临时的——如果 flush 失败，下次 compaction 时对话文本已丢失（被压缩），事件无法重新提取。

**Fix Suggestion:** 在 `flush()` 中添加 try-except，写入失败时记录日志并至少将事件文本暂存，避免因磁盘 I/O 错误导致不可恢复的记忆丢失。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-ARCH-22: frontmatter.py 解析器不支持多行值和嵌套结构

**Description:** `parse_frontmatter()`（frontmatter.py:47-55）只支持扁平 `key: value` 格式，不支持 YAML 多行值（`|`、`>`）、列表（`- item`）、嵌套结构。当前 `format_frontmatter()` 生成的 frontmatter 只包含简单字符串值（name、description、type），所以解析器够用。但如果未来 frontmatter 需要包含列表或结构化数据，解析器会静默返回不完整的结果。

**File Location:** `framework/agent_framework/memory/frontmatter.py:47-55`

**Impact:** 当前使用场景下无影响。但 `_yaml_string()` 的引号转义逻辑（行 6-19）与 `parse_frontmatter_lines()` 的反向解析（行 41-42）之间存在对称性——生成时用 `\\"` 转义，解析时用 `\\"` → `"` 反转义，但 `\\` → `\` 只反转义一次，不支持多层转义。

**Fix Suggestion:** 如果不需要复杂 YAML，当前实现足够。如需扩展，考虑引入 `pyyaml` 依赖或明确文档化当前解析器的限制。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-18: index_manager.update() 截断逻辑可能丢失最新条目

**Description:** `MemoryIndexManager.update()`（index_manager.py:76-89）在索引超过 `_MAX_LINES=200` 行时执行截断，保留 header 行 + body 的最后 N 行。但截断逻辑先做 `header/body` 分离（基于是否以 `#` 开头或空行），然后保留 `body[-max_body:]`。这意味着最早的 body 条目被丢弃，但如果早期条目仍然有效（对应的记忆文件仍然存在），索引会变得不完整——某些记忆文件存在但不在索引中。

**File Location:** `framework/agent_framework/memory/index_manager.py:76-89`

**Impact:** 索引截断导致部分记忆文件在 MEMORY.md 中不可见。`LLMScoringRetriever._scan_candidates()` 不依赖 MEMORY.md（它直接 glob 文件），所以搜索不受影响。但 MEMORY.md 作为人可读的索引会变得不完整。

**Fix Suggestion:** 截断时应移除对应记忆文件已不存在的条目（先 clean 再 truncate），或将 `_MAX_LINES` 提高到足够容纳所有活跃记忆。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-19: semantic_writer._detect_overlap 关键词匹配过于宽松

**Description:** `SemanticWriter._detect_overlap()`（semantic_writer.py:109-123）使用 `re.findall(r"[\w一-鿿]{2,}", why_phrase)` 从新记忆的 Why 行提取关键词，然后逐个检查是否出现在已有内容中。但匹配粒度太细：(1) 2 个字符以上的任何连续中文字符都算关键词，导致大量误匹配。(2) 只要有任何一个关键词在已有内容中出现，就报告"重叠"——但这个关键词可能只是常见的两个字（如"代码"、"测试"），在多个不相关的记忆中出现。(3) 重叠检测只记录 warning（行 129），不阻止写入——merge 仍然执行（行 132-133），所以重叠检测的实际效果只是日志记录。

**File Location:** `framework/agent_framework/memory/semantic_writer.py:109-123,128-133`

**Impact:** 重叠检测几乎总是触发 warning（常见词汇如"代码"、"用户"、"系统"容易匹配），导致 warning 日志噪音。但实际行为不受影响——merge 照常执行。

**Fix Suggestion:** (1) 提高匹配阈值：要求至少 2 个关键词同时出现才算重叠，或要求关键词长度 >= 3。(2) 或将重叠检测改为主动去重策略——发现重叠时跳过写入而非仅记录 warning。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

### LOW

#### FRMW-ARCH-23: search.py 每次调用创建新的 EpisodicLogManager 实例

**Description:** `handle_memory_search()`（search.py:25）每次被调用时都创建新的 `EpisodicLogManager(memory_dir=Path(memory_dir))` 实例。虽然 `EpisodicLogManager.__init__` 只保存一个 `Path` 引用（无状态初始化），开销可忽略，但创建不必要的对象实例不符合最佳实践。更重要的是，`memory_dir` 从 `ctx.extra.get("memory_dir")` 获取（行 20），如果 `memory_dir` 值为字符串而非 Path，`Path(memory_dir)` 转换在每次调用时重复执行。

**File Location:** `framework/agent_framework/memory/search.py:20-25`

**Impact:** 性能影响可忽略。但如果 `memory_dir` 未配置，handler 返回错误消息但不引导用户如何配置。

**Fix Suggestion:** 在 ToolUseContext 初始化时创建 `MemoryStore` 实例，handler 直接调用 `store.search()` 而非自行组装底层组件。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

#### FRMW-ARCH-24: semantic_extractor.py _call_llm 解析失败静默返回空列表

**Description:** `SemanticExtractor._call_llm()`（semantic_extractor.py:95-99）在 LLM 返回非法 JSON 时 `logger.warning` 并返回空列表 `[]`。对于格式不完整的单个记忆候选（行 113-114），同样 `logger.warning` 并 `continue` 跳过。这意味着语义提取失败是完全静默的——调用方（`AgentLoop` 的 memory flush 路径）无法区分"没有值得提取的内容"和"LLM 返回格式错误导致提取失败"。

**File Location:** `framework/agent_framework/memory/semantic_extractor.py:95-99,113-114`

**Impact:** 语义提取失败被静默吞掉，无法追踪提取质量。对于 best-effort 设计可以接受，但缺少指标来评估提取器的实际效果。

**Fix Suggestion:** 在 `_call_llm` 返回值中区分"无内容"和"解析失败"，或在 `SemanticExtractor` 上添加计数器追踪成功/失败率。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

---

## safety/

逐文件审查范围：4 个源文件，~315 行（boundary.py 36 行、permissions.py 111 行、verification.py 69 行、hitl.py 66 行）。
模块职责：路径沙箱、命令策略（预留）、权限管道、验证循环、人机回环。

### CRITICAL

*(none found)*

### HIGH

#### FRMW-ARCH-25: CommandPolicy 占位接口无任何实施逻辑

**Description:** `boundary.py:28-36` 中 `CommandPolicy` 是一个 Pydantic `BaseModel`，包含 `allowed_commands`、`blocked_commands`、`allow_pipes`、`allow_redirects`、`safe_env_vars` 五个字段，全部有默认值（空列表或 False）。但没有任何代码使用 `CommandPolicy`——没有实例化、没有验证逻辑、没有集成到工具执行路径。这个类的文档注释说"预留接口，bash 工具实现后启用"，但如果在 `CommandPolicy` 实施之前就添加了 bash/exec 工具，agents 可以执行任意命令而没有任何沙箱保护。

**File Location:** `framework/agent_framework/safety/boundary.py:28-36`

**Impact:** 安全边界存在但未激活。当前唯一的命令防护是 `safe_path()` 函数（仅保护文件路径），对 shell 命令执行无任何约束。如果 bash 工具被添加而不先实施 `CommandPolicy`，将导致命令注入漏洞。

**Fix Suggestion:** (1) 在添加 bash/exec 类工具之前，必须先实现 `CommandPolicy` 的验证逻辑（解析命令、检查前缀、禁止管道/重定向）。(2) 或将 `CommandPolicy` 标记为实验性 API 并在文档中明确说明限制。(3) 添加集成测试确保 `CommandPolicy` 在 bash 工具路径中被调用。

**Priority:** HIGH
**Related:** FRMW-03 (设计问题)

---

#### FRMW-SEC-19: _CRITICAL_TOOLS 全局空集合，DENY 第一级永远不触发

**Description:** `permissions.py:40` 定义 `_CRITICAL_TOOLS: set[str] = set()`，这是一个模块级全局空集合。`PermissionPipeline.check()`（行 58）首先检查 `tool_name in _CRITICAL_TOOLS`，但由于集合始终为空，检查永远返回 False。整个 DENY 第一级形同虚设。没有任何 API 允许向 `_CRITICAL_TOOLS` 添加工具名——它不在 `PermissionPipeline.__init__` 参数中，不在配置文件中，也没有 `add_critical_tool()` 函数。

**File Location:** `framework/agent_framework/safety/permissions.py:40,58`

**Impact:** 安全模型中设计的高危工具强制拒绝机制从未生效。如果未来添加需要强制拒绝的高危工具（如 `execute_sql`、`delete_all`），没有标准化的方式将其标记为 CRITICAL。

**Fix Suggestion:** (1) 将 `_CRITICAL_TOOLS` 改为可配置（通过 `PermissionPipeline.__init__` 参数传入）。(2) 或移除这个空集合，只保留 profile 级别的 `disallowed_tools` 做黑名单。(3) 如果保留，至少添加 `add_critical_tool()` 函数允许运行时注册。

**Priority:** HIGH
**Related:** FRMW-04 (安全审查)

---

#### FRMW-LOGIC-20: VerificationRunner 5 种检查类型只实现 regex_match，其余静默返回 None

**Description:** `VerificationRunner._run_single()`（verification.py:48-53）对 `VerificationRule.check` 字段只处理 `regex_match` 分支，对其余 4 种检查类型（`code_compiles`、`tests_pass`、`schema_valid`、`llm_judge`）直接返回 `None`。`run_post_tool()`（行 43-44）会过滤掉 `None` 结果，意味着这 4 种检查类型的规则会被静默跳过——规则存在但从不执行，不会产生任何验证结果（包括"跳过"警告）。

**File Location:** `framework/agent_framework/safety/verification.py:48-53`

**Impact:** 如果用户配置了 `check: "tests_pass"` 的验证规则，期望工具执行后运行测试，但规则永远不会执行。这给用户错误的信心——以为验证在工作，实际上只有 `regex_match` 类型的规则生效。

**Fix Suggestion:** (1) 实现剩余 4 种检查类型，或 (2) 对未实现的类型抛出 `NotImplementedError` 而非静默返回 None，让调用方明确知道规则未生效。(3) 或从 `Literal` 类型中移除未实现的类型，只保留 `regex_match`，并将其余类型标记为 TODO。

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-LOGIC-21: hitl.py 使用已弃用的 asyncio.get_running_loop()（原 CONCERNS.md 记载为 get_event_loop）

**Description:** `hitl.py:47` 使用 `asyncio.get_running_loop()` 获取当前事件循环。CONCERNS.md 记载此为 `asyncio.get_event_loop()`（Python 3.10+ 已弃用），但当前代码已修正为 `get_running_loop()`。`get_running_loop()` 在有运行中的事件循环时行为正确。但如果 `create_pending()` 在非 async 上下文中被调用（如从同步代码直接调用），会抛出 `RuntimeError: no running event loop`。此外，`HITLManager` 整体未接线到 `ToolRouter.dispatch()`——权限管道的 ASK 决策不触发 HITL 交互。

**File Location:** `framework/agent_framework/safety/hitl.py:47`

**Impact:** `get_running_loop()` 本身已修正，不再是弃用 API 问题。但 HITL 系统整体未集成到工具执行路径——`HITLManager` 存在但从未在 `ToolRouter` 中使用，ASK 决策直接返回错误（参见 FRMW-LOGIC-05）。这意味着 HITL 机制是一个独立的、未使用的安全组件。

**Fix Suggestion:** (1) 将 `HITLManager` 集成到 `ToolRouter.dispatch()` 的 ASK 决策路径中。(2) 当 `PermissionPipeline.check()` 返回 ASK 时，创建 `PermissionRequest`，等待用户响应后继续或拒绝执行。(3) 文档中明确说明当前 HITL 是未使用的预留接口。

**Priority:** HIGH
**Related:** FRMW-02 (逻辑漏洞)

---

### MEDIUM

#### FRMW-SEC-20: safe_path 不检查目标是否为符号链接目录

**Description:** `safe_path()`（boundary.py:17-25）使用 `(workdir / p).resolve()` 解析路径，`resolve()` 会跟随所有符号链接并返回绝对路径，然后检查 `resolved.is_relative_to(workdir_resolved)`。这正确处理了 `../../` 绕过和单层符号链接。但如果 `workdir` 本身包含指向外部的符号链接（如 `workdir = /tmp/link`，`/tmp/link -> /outside`），`workdir.resolve()` 也会跟随，可能导致 `workdir_resolved` 指向意外位置。此外，`resolve()` 在路径不存在时的行为依赖操作系统——某些系统可能不解析不存在的路径组件的符号链接。

**File Location:** `framework/agent_framework/safety/boundary.py:17-25`

**Impact:** 在当前使用场景下（`workdir` 由应用配置控制，不受用户输入影响），风险极低。但如果未来允许用户自定义 `workdir`，需要额外验证 `workdir` 本身的安全性。

**Fix Suggestion:** 添加 `workdir.resolve()` 的验证（确保解析后的路径在预期范围内），或在文档中明确说明 `workdir` 必须由受信任的配置提供。

**Priority:** MEDIUM
**Related:** FRMW-04 (安全审查)

---

#### FRMW-ARCH-26: PermissionResult 使用手写 class 而非 Pydantic BaseModel

**Description:** `PermissionResult`（permissions.py:25-36）使用手写 `class` + `__init__` 而非 `Pydantic BaseModel`，与同模块的 `PermissionOption`、`PermissionRequest`、`PermissionResponse`（hitl.py 中使用 BaseModel）不一致。`PermissionResult` 也没有 `__eq__`、`__repr__` 等方法，测试时难以断言结果。

**File Location:** `framework/agent_framework/safety/permissions.py:25-36`

**Impact:** 风格不一致，但功能正确。测试代码中需要手动比较字段而非直接 `assert result == expected`。

**Fix Suggestion:** 改为 `class PermissionResult(BaseModel):`，统一模块内的数据模型风格。

**Priority:** MEDIUM
**Related:** FRMW-03 (设计问题)

---

#### FRMW-LOGIC-22: PermissionPipeline._annotate_decision 无注解工具默认 ASK

**Description:** `PermissionPipeline._annotate_decision()`（permissions.py:80-110）在工具没有注册任何注解（`annotations` 为空 dict）时，所有布尔检查都返回 False，最终落到行 110 返回 `PermissionDecision.ASK, "unknown", RiskLevel.LOW`。这意味着所有未注册注解的未知工具都会触发 ASK 决策。结合 FRMW-LOGIC-05（ASK 决策在 router 中被当作错误返回），未注解的工具会被静默拒绝。

**File Location:** `framework/agent_framework/safety/permissions.py:109-110`

**Impact:** 新注册的工具如果没有通过 `register_annotations()` 提供注解，在非 accept 模式下会被 ASK 拒绝。这是一个隐性门槛——开发者可能不知道需要注册注解才能让工具正常工作。

**Fix Suggestion:** (1) 在 `ToolSpec` 中添加默认注解（如 `readOnly=False, destructive=False`），让 `PermissionPipeline` 在工具注册时自动获取注解。(2) 或对未知工具默认 ALLOW 而非 ASK（更宽松但更友好）。(3) 至少在文档中说明注解注册的必要性。

**Priority:** MEDIUM
**Related:** FRMW-02 (逻辑漏洞)

---

### LOW

#### FRMW-ARCH-27: verification.py _check_regex 不处理 field 不存在的场景

**Description:** `_check_regex()`（verification.py:55-68）使用 `tool_input.get(field, "")` 获取字段值，如果 `field` 不存在则使用空字符串 `""`。空字符串与任何模式匹配的结果取决于模式——如果模式是 `.*`，空字符串匹配成功；如果是 `.+`，空字符串匹配失败。这可能导致"字段不存在"和"字段为空"产生不同的验证结果，但用户难以区分。

**File Location:** `framework/agent_framework/safety/verification.py:57-59`

**Impact:** 验证规则的配置需要了解空值的匹配行为。当前无实际 bug 报告。

**Fix Suggestion:** 对字段不存在的情况返回 `passed=False, detail="字段 '{field}' 不存在"`，明确区分"缺失"和"不匹配"。

**Priority:** LOW
**Related:** FRMW-02 (逻辑漏洞)

---

#### FRMW-ARCH-28: HITLManager._pending dict 无大小限制

**Description:** `HITLManager._pending`（hitl.py:43）是一个无限增长的 dict，存储 `request_id -> Future` 映射。如果权限请求不断创建但从未被 resolve（如 UI 层不响应），`_pending` 会持续增长。虽然 `cancel_all()` 方法可以清空所有待处理请求，但需要外部代码主动调用。

**File Location:** `framework/agent_framework/safety/hitl.py:43`

**Impact:** 在正常使用场景下，权限请求应及时被 resolve 或 cancel。但由于 HITL 当前未接线（参见 FRMW-LOGIC-21），`_pending` 实际从未被使用。

**Fix Suggestion:** 添加最大待处理请求数限制，超限时自动取消最旧的请求。或在 `create_pending` 中设置 Future 的超时。

**Priority:** LOW
**Related:** FRMW-03 (设计问题)

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
