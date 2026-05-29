# Phase 2: 安全审查与修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 2-安全审查与修复
**Areas discussed:** MCP env 防护策略, API Key 保护方案, Permission ASK 接线范围, SECURITY-REVIEW.md 报告格式

---

## MCP 环境变量注入防护

### 防护策略选择

| Option | Description | Selected |
|--------|-------------|----------|
| 黑名单阻止 | 阻止已知敏感 key（API_KEY、TOKEN 等）被覆盖。灵活但需维护名单。 | ✓ |
| 白名单放行 | 只允许安全的 key 被覆盖（PATH、HOME 等）。更严格但可能阻碍合法 MCP server。 | |
| 完全隔离 | 不合并 os.environ，只传用户 env + PATH。最严格但可能破坏依赖系统 env 的 server。 | |

**User's choice:** 黑名单阻止
**Notes:** 黑名单策略在灵活性和安全性之间取得平衡。

### 执行层级选择

| Option | Description | Selected |
|--------|-------------|----------|
| Config 级 | 在 McpServerConfig 校验时拒绝敏感 key，错误信息更早更清晰。 | ✓ |
| Transport 级静默过滤 | 在 StdioTransport 启动子进程前过滤掉敏感 key，不报错。 | |
| 双层防护 | Config 级报错 + Transport 级兜底过滤。更安全但稍复杂。 | |

**User's choice:** Config 级
**Notes:** 更早发现错误，减少调试成本。

### 匹配规则选择

| Option | Description | Selected |
|--------|-------------|----------|
| 关键词匹配 | 匹配含有 API_KEY、TOKEN、SECRET 等关键词的 key（不区分大小写）。覆盖面广。 | ✓ |
| 精确名单 | 维护精确的 key 名单（如 OPENAI_API_KEY）。精确但需随新 provider 更新。 | |
| Claude decide | 由 Claude 选最合理的方案。 | |

**User's choice:** 关键词匹配
**Notes:** 降低维护成本，覆盖未知 provider 的敏感变量。

---

## API Key 保护方案

### 保护方式选择

| Option | Description | Selected |
|--------|-------------|----------|
| 构造后清除 | httpx client 构造后立即 clear _api_key。简单直接。 | |
| SecretStr 包装 | 用 Pydantic SecretStr 包装，__repr__ 自动脱敏，可重建 client。 | ✓ |
| 仅日志脱敏 | 保持现有存储，在 __repr__/__str__ 中过滤。最小改动。 | |

**User's choice:** SecretStr 包装
**Notes:** 用户在得知"构造后清除"会导致无法重建 client 后，主动选择 SecretStr 方案。

### 统一范围

| Option | Description | Selected |
|--------|-------------|----------|
| 统一 3 Provider | 3 个 Provider 都使用 SecretStr，保持一致。 | ✓ |
| 仅主要 Provider | 仅 Anthropic/OpenAI 改，DeepSeek 保持现状。 | |

**User's choice:** 统一 3 Provider

---

## Permission ASK 接线范围

### 接线程度选择

| Option | Description | Selected |
|--------|-------------|----------|
| 全面接线 HITL | 将 HITLManager 接入 ToolRouter，使 ASK 触发用户确认。完整但涉及跨模块开发。 | |
| 文档化缺口 | 在 SECURITY-REVIEW.md 中记录缺口 + 改进路径。保持 phase 范围可控。 | ✓ |
| Claude decide | 由 Claude 决定。 | |

**User's choice:** 文档化缺口
**Notes:** 全面接线涉及新功能开发，可能超出"安全审查与修复"的范围。

---

## SECURITY-REVIEW.md 报告格式

### 组织方式选择

| Option | Description | Selected |
|--------|-------------|----------|
| 按严重性分级 | 按 CRITICAL/HIGH/MEDIUM/LOW 组织，每项含描述+位置+状态+方案。安全报告行业惯例。 | ✓ |
| 按模块分类 | 按 tools/、llm/、safety/ 等模块分类。便于跟踪各模块安全状态。 | |
| 混合结构 | 主结构按严重性，每级下按模块分组。信息密度高但稍复杂。 | |

**User's choice:** 按严重性分级

### 内容深度选择

| Option | Description | Selected |
|--------|-------------|----------|
| 精简报告 | 每个问题：描述 + 文件位置 + 严重性 + 修复状态。 | ✓ |
| 详细报告 | 额外包括代码 diff 链接、修复 PR、回归测试结果。 | |

**User's choice:** 精简报告

---

## Claude's Discretion

- Hook 命令执行安全（#4）文档化程度
- MessageBus 可预测路径（#6）文档化建议
- 黑名单关键词列表具体内容
- 测试组织方式

## Deferred Ideas

None — discussion stayed within phase scope
