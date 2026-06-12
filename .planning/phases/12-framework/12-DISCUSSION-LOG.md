# Phase 12: Framework 代码审查 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 12-Framework 代码审查
**Areas discussed:** 审查基线与覆盖度, 审查方法与工具, 报告格式与分级标准

---

## 审查基线与覆盖度

### 审查覆盖范围

| Option | Description | Selected |
|--------|-------------|----------|
| 全面重新审查 | 逐文件审查所有源码，与 v0.0.1 基线对照标注"已修复/新增/持续" | ✓ |
| 增量审查 | 只审查 v0.0.2/v0.0.3 新增/变更模块 | |
| 基于 CONCERNS.md 补充 | 在已有问题清单基础上补充漏检项 | |

**User's choice:** 全面重新审查
**Notes:** 用户希望独立、全面地审查所有框架层代码

### 模块重点分配

| Option | Description | Selected |
|--------|-------------|----------|
| 全模块等权审查 | 所有模块同等深度审查 | ✓ |
| 新模块重点 + 旧模块快速扫描 | v0.0.2/v0.0.3 新增模块重点审查 | |
| 仅高风险模块 | 只审查 agents/, tools/, safety/ | |

**User's choice:** 全模块等权审查
**Notes:** 所有模块同等待遇，不偏重

### 与旧审查对照方式

| Option | Description | Selected |
|--------|-------------|----------|
| 与 v0.0.1 逐项对照 | 每个 issue 标注已修复/持续/新增 | |
| 仅标注完全重复项 | 只标注位置和描述一致的 | |
| 不对照，独立审查 | 独立产出，后续手动对比 | ✓ |

**User's choice:** 不对照，独立审查
**Notes:** 完全独立审查，不依赖旧报告

---

## 审查方法与工具

### 死代码检测工具

| Option | Description | Selected |
|--------|-------------|----------|
| ruff | Python 生态最活跃 linter，可检测未使用 import/变量/函数 | ✓ |
| vulture | 专门检测死代码，误报率低 | |
| ruff + vulture 组合 | 覆盖最全 | |

**User's choice:** ruff

### 审查流程组织

| Option | Description | Selected |
|--------|-------------|----------|
| 工具先行 + 人工审查 | 先 ruff 扫描，再逐模块人工审查 | ✓ |
| 纯人工审查 | 不用自动化工具 | |
| 并行子任务审查 | 拆分为多个并行子任务 | |

**User's choice:** 工具先行 + 人工审查

### 审查范围（测试代码）

| Option | Description | Selected |
|--------|-------------|----------|
| 仅源码 | 只审查 agent_framework/ 下的 .py 文件 | ✓ |
| 源码 + 测试代码 | 连测试代码也审查 | |

**User's choice:** 仅源码

---

## 报告格式与分级标准

### 严重性分级标准

| Option | Description | Selected |
|--------|-------------|----------|
| 影响导向分级 | CRITICAL=数据丢失/安全漏洞, HIGH=逻辑错误, MEDIUM=代码质量, LOW=风格 | ✓ |
| 修复紧迫度分级 | 按修复紧急程度分级 | |
| You decide | Claude 自行定义 | |

**User's choice:** 影响导向分级

### 报告组织结构

| Option | Description | Selected |
|--------|-------------|----------|
| 按严重性分组 | CRITICAL → HIGH → MEDIUM → LOW | |
| 按模块分组 | 每个模块一个章节，模块内按严重性排序 | ✓ |
| 按问题类型分组 | 安全/逻辑/设计/死代码分组 | |

**User's choice:** 按模块分组

### Issue 字段

| Option | Description | Selected |
|--------|-------------|----------|
| 详细字段 | ID、描述、文件:行号、影响、修复建议、优先级 | ✓ |
| 简要字段 | 描述、文件位置、优先级 | |
| You decide | Claude 自行决定 | |

**User's choice:** 详细字段

---

## Claude's Discretion

- ruff 的具体规则配置和启用项
- 模块审查的先后顺序
- 具体 issue ID 编号方案
- 跨模块问题的归类方式

## Deferred Ideas

None — discussion stayed within phase scope
