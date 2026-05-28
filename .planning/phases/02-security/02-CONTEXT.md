# Phase 2: 安全审查与修复 - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

审查并修复框架层（`framework/agent_framework/`）中 6 个已知安全问题，产出 SECURITY-REVIEW.md，修复所有 CRITICAL 级别问题。

**问题列表：**
1. 文件工具缺少路径沙箱（CRITICAL）— `safe_path()` 已存在但未被调用
2. MCP 环境变量注入（HIGH）— `StdioTransport` 盲目合并 `env`
3. API Key 明文存储（MEDIUM）— 3 个 Provider 存 `self._api_key` 明文
4. Hook 命令执行任意 shell（MEDIUM）— `trusted` flag 存在但需文档化
5. Permission ASK 未接入 HITL（MEDIUM）— 返回错误而非用户确认
6. MessageBus 可预测文件路径（LOW）— 文档化即可

**范围：** 仅修复安全问题，不做架构重构。产出 SECURITY-REVIEW.md 结构化报告。

</domain>

<decisions>
## Implementation Decisions

### 文件路径沙箱（CRITICAL #1）
- **D-01:** 在 `read_file` 和 `write_file` 中调用 `safe_path(path, ctx.working_dir)` 校验路径，拒绝逃出工作目录的请求
- **D-02:** 路径逃出时返回 `ToolResult(is_error=True)` 而非抛异常（保持工具层错误模式一致）
- **D-03:** 错误消息不暴露实际路径信息，使用通用提示

### MCP 环境变量注入（HIGH #2）
- **D-04:** 使用黑名单策略阻止敏感环境变量被覆盖
- **D-05:** 在 Config 级（`McpServerConfig` 校验时）执行检查，配置加载时即报错
- **D-06:** 黑名单匹配规则使用关键词匹配（不区分大小写匹配 API_KEY、TOKEN、SECRET、PASSWORD、CREDENTIAL 等模式）

### API Key 保护（MEDIUM #3）
- **D-07:** 3 个 Provider 统一使用 `pydantic.SecretStr` 包装 `_api_key`
- **D-08:** `__repr__`、`__str__` 自动脱敏，但 key 仍可用于重建 httpx client

### Permission ASK → HITL（MEDIUM #5）
- **D-09:** 文档化此缺口，不在本 phase 全面接线 HITL。在 SECURITY-REVIEW.md 中记录改进路径

### SECURITY-REVIEW.md 格式
- **D-10:** 按严重性分级组织（CRITICAL / HIGH / MEDIUM / LOW）
- **D-11:** 精简报告：每个问题含描述 + 文件位置 + 严重性 + 修复状态

### Claude's Discretion
- Hook 命令执行安全（#4）的文档化程度由 planner 决定
- MessageBus 可预测路径（#6）的文档化建议由 planner 决定
- 黑名单关键词列表的具体内容由 researcher/planner 根据行业最佳实践确定
- 测试组织方式（新测试文件 vs 追加到现有文件）由 planner 决定

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 安全问题详情
- `.planning/codebase/CONCERNS.md` §Security Considerations — 6 个安全问题的触发条件、文件位置、影响分析
- `.planning/REQUIREMENTS.md` §R1: 安全审查 — 验收标准和已知安全问题列表

### 架构与代码结构
- `.planning/codebase/ARCHITECTURE.md` — 模块依赖关系和数据流（Safety Layer 描述）
- `.planning/codebase/STRUCTURE.md` — 文件结构、模块位置
- `.planning/codebase/CONVENTIONS.md` — 编码规范，修复需遵循

### 核心源文件
- `framework/agent_framework/safety/boundary.py` — `safe_path()` 函数、`PathEscapesWorkspace` 异常
- `framework/agent_framework/tools/builtin/file_tools.py` — 需调用 `safe_path()` 的文件工具
- `framework/agent_framework/tools/mcp/config.py:27` — `McpServerConfig` env 字段
- `framework/agent_framework/tools/mcp/transport.py:57` — `StdioTransport` env 合并
- `framework/agent_framework/llm/providers/openai_provider.py:111` — `_api_key` 存储
- `framework/agent_framework/llm/providers/anthropic_provider.py:259` — `_api_key` 存储
- `framework/agent_framework/llm/providers/deepseek_provider.py:149` — `_api_key` 存储
- `framework/agent_framework/tools/router.py:72-76` — ASK 决策处理
- `framework/agent_framework/safety/hitl.py` — HITL 系统（未接线）
- `framework/agent_framework/hooks/manager.py:120-122` — Hook 命令执行

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `framework/agent_framework/safety/boundary.py:17-25` — `safe_path()` 已实现（resolve + is_relative_to 校验），直接调用即可
- `framework/tests/test_boundary.py` — `safe_path` 测试已存在，修复可参考
- `framework/tests/test_builtin_tools.py` — 文件工具测试，沙箱测试应追加于此

### Established Patterns
- 工具错误模式：所有工具返回 `ToolResult(is_error=True)` 而非抛异常
- Pydantic v2 模式：框架使用 Pydantic BaseModel，`SecretStr` 是内置类型
- Config 校验模式：Pydantic `@model_validator` 或 `@field_validator` 用于字段级校验

### Integration Points
- `file_tools.py:12,26` — `Path(ctx.working_dir) / path` 是路径构建点，需在 resolve 后调用 `safe_path`
- `tools/mcp/config.py:27` — `McpServerConfig` 的 `env` 字段，需添加 validator
- `llm/providers/*.py` 的 `__init__` — `_api_key` 赋值点，需改为 `SecretStr`

</code_context>

<specifics>
## Specific Ideas

无特定参考 — 修复方案遵循最小改动原则，仅修复安全问题本身。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 2-安全审查与修复*
*Context gathered: 2026-05-28*
