# Phase 25: Address Tech Debt — Integration Warnings + Stale Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 25-tech-debt-integration-warnings-stale-docs
**Areas discussed:** Asyncio warnings verification, stale docs update scope

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Asyncio 警告验证策略 | 当前测试零 asyncio 警告，ROADMAP 假设有警告需修复 | |
| 过时文档更新深度 | README/REQUIREMENTS/PROJECT/CONCERNS 均过时，最小更新 vs 全面刷新 | |
| CONCERNS.md 处理方式 | 已解决问题标记 ✅Resolved 还是直接删除 | |
| 你决定 | 纯清理工作，让 Claude 自行判断 | ✓ |

**User's choice:** 你决定
**Notes:** 用户信任 Claude 自行做出所有清理决策，无需逐一讨论。

---

## Claude's Discretion

用户选择"你决定"，以下决策由 Claude 基于分析做出：

1. **Asyncio 警告** — 采用双层验证（标准 `-W all` + strict deprecation），确认零警告后从 STATE.md 移除 deferred 条目
2. **过时文档** — 全面刷新策略（非最小修补），因为 v0.0.6 是 milestone 收尾，文档应准确反映完成状态
3. **CONCERNS.md** — 标记 ✅Resolved（保留历史记录），不删除已解决问题
4. **REQUIREMENTS.md** — 批量更新 13 项已完成需求 + 可追溯性表
5. **README.md** — 修正错误类名、补充缺失模块、更新 roadmap 和测试数量

## Deferred Ideas

None — discussion stayed within phase scope
