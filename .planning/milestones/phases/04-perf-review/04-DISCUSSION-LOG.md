# Phase 4: 性能与数据安全审查 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 4-性能与数据安全审查
**Areas discussed:** MessageBus 原子读写方案, MCP 逐字节读取修复, PERF-REVIEW.md 报告格式

---

## MessageBus 原子读写方案

| Option | Description | Selected |
|--------|-------------|----------|
| rename swap | 读原文件 → 写空内容到 temp → os.replace(temp, original)。框架已有 _atomic_write 先例。 | ✓ |
| 读+备份+清零三步原子 | 先 rename 原文件到 .backup（原子），然后读 .backup，最后 delete .backup。彻底无窗口。 | |
| 你决定 | Claude 根据已有代码模式自行选择。 | |

**User's choice:** rename swap
**Notes:** 选择与框架已有 _atomic_write 模式一致的方案。

### 清零失败处理

| Option | Description | Selected |
|--------|-------------|----------|
| 不重试，log warning | 清零失败保留已读取消息，仅 log warning。下次重复读取但不丢失。 | ✓ |
| 重试一次 | try/except 包裹，失败重试一次。更健壮但复杂度增加。 | |
| 你决定 | Claude 决定。 | |

**User's choice:** 不重试，log warning
**Notes:** 与 Phase 1 D-02 策略一致。

### 测试位置

| Option | Description | Selected |
|--------|-------------|----------|
| 追加到 test_teams_bus.py | 保持测试文件组织一致。 | ✓ |
| 新建测试文件 | 新建 test_msgbus_atomic.py。 | |
| 你决定 | Claude 决定。 | |

**User's choice:** 追加到 test_teams_bus.py

---

## MCP 逐字节读取修复

| Option | Description | Selected |
|--------|-------------|----------|
| readline() 循环 | asyncio StreamReader 自带缓冲区，连续读到空行检测 header 结束。大幅减少系统调用。 | ✓ |
| 分块读取 + 缓冲区 | 用更大 chunk（如 4096）读取，手动管理缓冲区。复杂度更高。 | |
| 你决定 | Claude 决定。 | |

**User's choice:** readline() 循环
**Notes:** MCP header 以 `\r\n\r\n` 结尾，需连续读空行检测。

### 测试位置

| Option | Description | Selected |
|--------|-------------|----------|
| 追加到 test_mcp_transport.py | 保持测试文件组织一致。 | ✓ |
| 新建测试文件 | 新建 test_mcp_header.py。 | |
| 你决定 | Claude 决定。 | |

**User's choice:** 追加到 test_mcp_transport.py

---

## PERF-REVIEW.md 报告格式

### 报告格式

| Option | Description | Selected |
|--------|-------------|----------|
| 精简格式 | 沿用 SECURITY-REVIEW.md：描述+文件位置+严重性+修复状态。 | ✓ |
| 增强格式 | 在精简格式基础上增加改进方案建议 + 预期收益评估。 | |
| 你决定 | Claude 决定。 | |

**User's choice:** 精简格式
**Notes:** 与已有 SECURITY-REVIEW.md 和 ARCH-REVIEW.md 风格一致。

### 报告内部组织

| Option | Description | Selected |
|--------|-------------|----------|
| 按修复状态分 | 分为"已修复"和"已记录"两大区域，每个区域内部按严重性排列。 | ✓ |
| 纯严重性排列 | 全部按 HIGH→MEDIUM→LOW 排列，不区分修复/记录。 | |
| 你决定 | Claude 决定。 | |

**User's choice:** 按修复状态分
**Notes:** 清晰区分代码修复项和纯文档记录项。

---

## Claude's Discretion

- rename swap 的临时文件命名和清理策略
- readline() 循环的具体实现细节（空行检测逻辑）
- PERF-REVIEW.md 中每个性能问题的具体描述措辞
- 测试函数命名和 fixture 使用方式

## Deferred Ideas

None — discussion stayed within phase scope
