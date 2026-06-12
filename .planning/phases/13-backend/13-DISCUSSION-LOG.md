# Phase 13: Backend 代码审查 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 13-Backend 代码审查
**Areas discussed:** 审查方法论沿用, Backend 安全审查维度, 跨层交叉参照策略, 审查范围与分 plan 策略

---

## 审查方法论沿用

| Option | Description | Selected |
|--------|-------------|----------|
| 完全沿用 Phase 12 方法论 | ruff + 人工审查流程、分级标准、issue 格式、按模块分组全部复用，使用 BKND- 前缀 | ✓ |
| 沿用但调整 | 沿用核心方法论，调整 scaffold 空文件处理等细节 | |
| 重新设计 | 根据 Backend 特点重新设计审查流程 | |

**User's choice:** 完全沿用 Phase 12 方法论
**Notes:** BKND- 前缀区分于 Phase 12 的 FRMW- 前缀

### Scaffold 空文件处理

| Option | Description | Selected |
|--------|-------------|----------|
| 仅标记为 scaffold，跳过 | 空文件只做确认记录，不展开详细审查 | ✓ |
| 全部审查，包括空文件 | 连空文件也纳入审查，检查模块结构合理性 | |

**User's choice:** 仅标记为 scaffold，跳过

### Issue ID 命名方案

| Option | Description | Selected |
|--------|-------------|----------|
| BKND- 前缀 | BKND-SEC-01、BKND-LOGIC-01、BKND-ARCH-01、BKND-DEAD-01 | ✓ |
| 其他 | 其他命名方案 | |

**User's choice:** BKND- 前缀

### 报告存放位置

| Option | Description | Selected |
|--------|-------------|----------|
| docs/reviews/ | 与 REVIEW-FRAMEWORK.md 同级，集中管理 | ✓ |
| phase 目录 | 放在 phase 目录下 | |

**User's choice:** docs/reviews/

---

## Backend 安全审查维度

| Option | Description | Selected |
|--------|-------------|----------|
| Web 安全全覆盖 | API 认证、输入验证、CORS、SQL 注入、认证绕过、敏感信息泄露、会话管理 | ✓ |
| 仅 Backend 特有 | 仅关注 Backend 特有安全问题 | |
| 其他 | 其他安全审查范围定义 | |

**User's choice:** Web 安全全覆盖

### 数据流追踪

| Option | Description | Selected |
|--------|-------------|----------|
| 完整数据流追踪 | 每个 API 端点追踪 HTTP 请求→参数解析→服务层→框架层→响应 | ✓ |
| 按模块审查，不追踪链路 | 仅按模块审查，不专门追踪跨层调用链 | |

**User's choice:** 完整数据流追踪

### 框架层调用审查

| Option | Description | Selected |
|--------|-------------|----------|
| 审查调用方式 | 检查是否正确使用框架层 API、是否有误用或不必要耦合 | ✓ |
| 不审查框架调用 | 仅关注 Backend 自身代码 | |

**User's choice:** 审查调用方式

---

## 跨层交叉参照策略

| Option | Description | Selected |
|--------|-------------|----------|
| 专题章节 + 主题归类 | 末尾设"跨层问题"章节，按主题归类，引用 FRMW issue ID | ✓ |
| 每个 issue 内联引用 | 在每个 Backend issue 中直接引用相关 Framework issue | |

**User's choice:** 专题章节 + 主题归类

### 交叉方向

| Option | Description | Selected |
|--------|-------------|----------|
| 单向：BKND → FRMW | 仅标注 Backend 发现中与 Framework 有关的问题 | ✓ |
| 双向对照 | 也检查 Framework 发现是否影响 Backend | |

**User's choice:** 单向：BKND → FRMW

---

## 审查范围与分 plan 策略

| Option | Description | Selected |
|--------|-------------|----------|
| 2 plans | Plan 1: ruff + 人工审查 + 数据流追踪；Plan 2: 交叉参照 + 汇总 | ✓ |
| 1 plan | 所有工作在一个 plan 内完成 | |
| 5 plans | 按 Phase 12 模式拆分 | |

**User's choice:** 2 plans

### 审查范围

| Option | Description | Selected |
|--------|-------------|----------|
| 仅源码 | 不含 tests/ 测试代码 | ✓ |
| 源码 + 测试 | 同时审查测试代码质量 | |

**User's choice:** 仅源码

### Plan 边界划分

| Option | Description | Selected |
|--------|-------------|----------|
| Plan 1: ruff + 审查 + 数据流 / Plan 2: 交叉参照 + 汇总 | 审查工作 vs 汇总工作分离 | ✓ |
| 其他划分 | 其他划分方式 | |

**User's choice:** Plan 1: ruff + 审查 + 数据流 / Plan 2: 交叉参照 + 汇总

---

## Claude's Discretion

- ruff 的具体规则配置和启用项
- 文件审查的先后顺序
- 跨层问题归类方式
- 数据流追踪的详细程度

## Deferred Ideas

None — discussion stayed within phase scope
