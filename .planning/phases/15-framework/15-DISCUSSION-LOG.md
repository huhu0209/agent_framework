# Phase 15: Framework 死代码与快速修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 15-Framework 死代码与快速修复
**Areas discussed:** Overall phase approach

---

## Phase Approach

| Option | Description | Selected |
|--------|-------------|----------|
| httpx 修复策略 | `from __future__ import annotations` vs 移入 TYPE_CHECKING guard | |
| 执行计划划分 | 单 plan vs 多 plan 按模块分步 | |
| 无需讨论，直接规划 | phase 足够机械性，Claude 自行判断实现 | ✓ |

**User's choice:** 无需讨论，直接规划
**Notes:** 用户认为这个 phase 是纯机械性清理工作，审查报告已精确定位所有问题，无需额外讨论实现细节。

---

## Claude's Discretion

- httpx 修复具体方案（`from __future__ import annotations` 或移入 TYPE_CHECKING guard）
- import 删除的顺序和分批方式
- 执行粒度（单 plan 或多 plan）
- 是否补充 logger 修复后的测试覆盖

## Deferred Ideas

None
