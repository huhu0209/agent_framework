# Phase 20: Config Foundation — Settings Model + Merge Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 20-Config Foundation — Settings Model + Merge Engine
**Areas discussed:** Settings 嵌套结构, 数组合并语义细节, config/ 文件布局

---

## Settings 嵌套结构

| Option | Description | Selected |
|--------|-------------|----------|
| 嵌套子模型 | Settings 包含 LlmConfig、ServerConfig 等子模型，env var 路径为 APP_LLM__PROVIDER | ✓ |
| 扁平字段 | Settings 直接包含 llm_provider、server_port 等扁平字段 | |
| 你决定 | 交给 Claude 选择 | |

**User's choice:** 你决定 → Claude 选择嵌套子模型
**Notes:** 用户先委托 Claude 决定，Claude 推荐嵌套子模型（与 JSON 结构对应、__ 分隔符天然支持、合并函数可递归）

| Option | Description | Selected |
|--------|-------------|----------|
| 仅全局运行时配置 | Settings 只含 model/llm/server/logging/permissions | ✓ |
| 全部配置集中管理 | 把模块配置也纳入 Settings | |
| 你决定 | 交给 Claude 选择 | |

**User's choice:** 仅全局运行时配置（推荐）
**Notes:** 与设计文档一致 — settings.json 只管跨模块全局配置，各模块靠 discover() 独立发现

| Option | Description | Selected |
|--------|-------------|----------|
| model 顶层 + llm 子模型 | model 顶层快速访问，llm 子模型含连接详情 | ✓ |
| model 移入 llm 子模型 | 更纯粹的嵌套 | |
| 你决定 | 交给 Claude 选择 | |

**User's choice:** model 顶层 + llm 子模型（推荐）

---

## 数组合并语义细节

| Option | Description | Selected |
|--------|-------------|----------|
| 低→高叠加，去重保序 | 全局在前、项目在后，高优先级重复则跳过 | ✓ |
| 高→低叠加 | 高优先级在前 | |
| 你决定 | 交给 Claude 选择 | |

**User's choice:** 低→高叠加，去重保序（推荐）

| Option | Description | Selected |
|--------|-------------|----------|
| 严格字符串全等 | "Bash(git *)" == "Bash(git *)" 但 ≠ "bash(git *)" | ✓ |
| 忽略大小写 | 更宽容但可能意外合并 | |
| 你决定 | 交给 Claude 选择 | |

**User's choice:** 严格字符串全等（推荐）

| Option | Description | Selected |
|--------|-------------|----------|
| 仅字符串列表 | Settings 数组字段都是 list[str] | |
| 支持字符串 + 对象列表 | 未来扩展，但 CFG-02 范围不需要 | |
| 你决定 | 交给 Claude 选择 | ✓ |

**User's choice:** 你决定 → Claude 选择仅字符串列表
**Notes:** Settings 中所有数组字段都是 list[str]，对象列表（mcp_servers）合并是 Phase 23 的职责

---

## config/ 文件布局

| Option | Description | Selected |
|--------|-------------|----------|
| 最小文件集 | 只建 settings.py + merge.py + __init__.py，避免空桩 | |
| 全部 4 文件 + 桩 | 现在 4 个文件，loader/discovery 留空 | |
| 你决定 | 交给 Claude 选择 | ✓ |

**User's choice:** 你决定 → Claude 选择最小文件集
**Notes:** 项目遵循"每个文件都有实际内容"惯例，loader.py 和 discovery.py 留到 Phase 21 创建

---

## Claude's Discretion

以下方面用户委托 Claude 决定：
1. Settings 模型组织方式 → Claude 选择嵌套子模型
2. _merge_settings() 数组类型范围 → Claude 选择仅 list[str]
3. config/ 文件布局 → Claude 选择最小文件集（3 文件）

## Deferred Ideas

None — discussion stayed within phase scope
