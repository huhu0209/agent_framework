# Phase 19: Frontend 全面修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 19-Frontend 全面修复
**Areas discussed:** SSE 验证粒度, Store 错误反馈机制, Auto-scroll 行为细节, Plan 分组策略

---

## SSE 验证粒度

### Q1: 验证粒度

| Option | Description | Selected |
|--------|-------------|----------|
| 轻量验证 | 仅验证 payload 是 object + 关键字段是 string，约 20 行代码 | ✓ |
| 完整 per-event schema | 为每种事件类型定义完整 zod schema，约 60-80 行 | |
| 手动 typeof 检查 | 不引入 zod，在 vizEventToBlock 内部用 typeof 检查 | |

**User's choice:** 轻量验证

### Q2: 验证位置

| Option | Description | Selected |
|--------|-------------|----------|
| parse 后验证 | JSON.parse 后、handleSseEvent 前插入验证，拦截最早 | ✓ |
| vizEventToBlock 内验证 | 在已有 typeof 检查基础上扩展 | |

**User's choice:** parse 后验证

### Q3: 验证失败行为

| Option | Description | Selected |
|--------|-------------|----------|
| 跳过 + console.warn | 跳过该事件继续处理，用户体验不受影响 | ✓ |
| 追加 error block | 向 streamingMessage 追加 error block 显示给用户 | |

**User's choice:** 跳过 + console.warn

### Q4: zod 依赖

| Option | Description | Selected |
|--------|-------------|----------|
| 添加 zod 依赖 | TS 生态标准验证库，bundle size ~13KB gzipped | ✓ |
| 手动 typeof 检查 | 无新依赖，但代码零散 | |

**User's choice:** 添加 zod 依赖

---

## Store 错误反馈机制

### Q1: 反馈方式

| Option | Description | Selected |
|--------|-------------|----------|
| Toast 通知 | 在顶部显示 Toast 通知，最常见前端错误反馈模式 | ✓ |
| 内联错误消息 | 在各操作区域显示内联错误 | |
| 仅 console.error | 最小改动但用户无感知 | |

**User's choice:** Toast 通知

### Q2: 状态管理

| Option | Description | Selected |
|--------|-------------|----------|
| Store 状态管理 | errorToast: string \| null + clearError() action | ✓ |
| 3秒自动消失 | setTimeout 自动清除 | |
| alert() | 最简单但 UX 差 | |

**User's choice:** Store 状态管理

### Q3: 覆盖范围

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 fetch 失败 | loadSessions、switchSession、deleteSession、renameSession 4 处 | |
| 所有网络错误场景 | 包括 SSE 解析失败、非 ok 响应等 | ✓ |

**User's choice:** 所有网络错误场景

### Q4: 消失策略

| Option | Description | Selected |
|--------|-------------|----------|
| 手动关闭 | 用户点击 X 或 Esc 关闭 | |
| 5秒自动消失 | setTimeout(5000) 自动清除 | ✓ |

**User's choice:** 5秒自动消失

---

## Auto-scroll 行为细节

### Q1: 滚动策略

| Option | Description | Selected |
|--------|-------------|----------|
| 智能 auto-scroll | 底部附近（100px）自动滚动，上滚后禁用 | ✓ |
| 总是滚动 | 每次新消息都滚动到底部 | |
| 新消息提示 + 手动 | 显示「新消息」按钮，用户点击才滚动 | |

**User's choice:** 智能 auto-scroll

### Q2: 底部判断方式

| Option | Description | Selected |
|--------|-------------|----------|
| scroll 位置判断 | parentRef.current.scrollTop + scrollHeight 判断 | |
| virtualizer API | 用 virtualizer 的 API 判断和执行 | ✓ |

**User's choice:** virtualizer API

### Q3: 底部阈值

| Option | Description | Selected |
|--------|-------------|----------|
| 100px | 宽松但不会打断正常浏览 | ✓ |
| 50px | 更严格 | |
| 200px | 非常宽松 | |

**User's choice:** 100px

### Q4: 初始加载滚动

| Option | Description | Selected |
|--------|-------------|----------|
| 是，初始加载也滚动 | 新会话、切换会话时自动滚动到底部 | ✓ |
| 仅流式消息滚动 | 初始加载保持之前滚动位置 | |

**User's choice:** 是，初始加载也滚动

---

## Plan 分组策略

### Q1: 分组方式

| Option | Description | Selected |
|--------|-------------|----------|
| 按文件分 2 plan | Plan A: store.ts (7 issues), Plan B: 组件 (4 issues) | ✓ |
| 按类型分 3 plan | 安全/逻辑/架构各一个 plan | |
| 按文件分 3 plan | store.ts / MessageList / 其余组件 | |

**User's choice:** 按文件分 2 plan

### Q2: 执行顺序

| Option | Description | Selected |
|--------|-------------|----------|
| store.ts 先行 | 核心数据层先修好，组件可引用新状态 | ✓ |
| 组件先行 | 简单组件先修，不依赖 store 改动 | |

**User's choice:** store.ts 先行

---

## Claude's Discretion

- zod 验证 schema 的具体字段定义和命名
- errorToast 组件的具体实现和样式
- virtualizer auto-scroll 的具体 API 使用方式
- toFrontendBlocks 运行时检查的具体实现
- groupBlocks orphan 处理的具体逻辑
- 每个 plan 内部的修复顺序

## Deferred Ideas

- FRNT-ARCH-10 (SessionItem 组件职责过多) — 需组件拆分重构
- FRNT-ARCH-12 (estimateSize 静态估计) — 需 measureElement 集成
- FRNT-ARCH-13 (ToolCallBlock result prop 类型过松) — 后续补测试时处理
- FRNT-ARCH-16 (Connected 状态硬编码) — 需后端 health endpoint
- FRNT-LOGIC-10 (clipboard 非 HTTPS 失败) — MEDIUM 级别
- 前端单元测试补写 — 需专门 milestone
