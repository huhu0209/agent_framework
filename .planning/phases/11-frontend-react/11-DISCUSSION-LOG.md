# Phase 11: Frontend React 集成 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 11-Frontend React 集成
**Areas discussed:** 页面布局与组件结构, 状态管理与事件流, WebSocket 连接策略, 配置表单与交互流程

---

## 页面布局与组件结构

### Canvas 与面板的布局关系

| Option | Description | Selected |
|--------|-------------|----------|
| 左 Canvas 右面板（推荐） | Canvas 固定 800×600 居左，右侧面板自适应填满剩余空间。面板内容从上到下：配置表单 → Agent 状态列表 → 事件日志。适合宽屏桌面。 | ✓ |
| 上 Canvas 下面板 | Canvas 在上方占全宽 800×600，下方是面板区域。适合窄屏。 | |
| 左面板 + 中 Canvas + 右面板 | 左侧窄面板，中间 Canvas，右侧窄面板。信息分散。 | |

**User's choice:** 左 Canvas 右面板（推荐）

### 右侧面板内容分区

| Option | Description | Selected |
|--------|-------------|----------|
| 单列纵向（推荐） | 配置表单 → Team 控制 → Agent 状态列表 → 事件日志。从上到下单列，每块有标题分隔。 | ✓ |
| 混合布局 | 上方横排配置+控制，下方左右分状态+日志。空间紧凑但可能拥挤。 | |
| Tab 切换式 | Tab 切换：创建 | 状态 | 日志。需要切换查看，不适合实时观察。 | |

**User's choice:** 单列纵向（推荐）

### 事件日志展示方式

| Option | Description | Selected |
|--------|-------------|----------|
| 固定高度 + 自动滚动（推荐） | 最多显示最近 50 条，自动滚动到最新。旧的被丢弃。简洁轻量。 | ✓ |
| 可调整高度 | 可拖拽调整高度。更灵活但实现复杂。 | |
| 无限制 + 全量历史 | 无数量限制，可滚动查看全部。长时间运行后积累大量事件。 | |

**User's choice:** 固定高度 + 自动滚动（推荐）

### 组件拆分粒度

| Option | Description | Selected |
|--------|-------------|----------|
| 按功能拆分组件（推荐） | 配置表单、Agent 状态、Team 控制、事件日志每个作为独立组件。清晰易维护。 | ✓ |
| 单文件内联 | 全部放在 App.tsx。快速但文件会很长。 | |
| You decide | 你来决定最合理的组件拆分方式。 | |

**User's choice:** 按功能拆分组件（推荐）

---

## 状态管理与事件流

### 状态管理方案

| Option | Description | Selected |
|--------|-------------|----------|
| useReducer + Context（推荐） | 单个 useReducer 处理所有 WebSocket 消息 + UI 状态，通过 Context 向下传递。与 CONC-02 的 reducer 统一分发完全匹配。 | ✓ |
| 外部状态库 | 引入 Zustand/Jotai 等。功能更强但增加依赖，MVP 不必要。 | |
| 纯 useState + props | 每个组件内部 useState。跨组件共享状态麻烦。 | |

**User's choice:** useReducer + Context（推荐）

### Reducer 拆分策略

| Option | Description | Selected |
|--------|-------------|----------|
| 单个 reducer（推荐） | 一个 reducer 处理所有 action 类型。state 包含 connection、agents、eventLog 三块。简单统一。 | ✓ |
| 多个 reducer 分离 | 连接状态、Agent 列表、事件日志各用一个 reducer。更细粒度但复杂。 | |
| You decide | 你来决定。 | |

**User's choice:** 单个 reducer（推荐）

### Agent 列表数据结构

| Option | Description | Selected |
|--------|-------------|----------|
| Map<name, AgentState>（推荐） | 用 Map 存储，VizEvent agent 字段作为 key。简单高效。 | ✓ |
| Array + find | 用数组存储，每次查找更新。查找效率低。 | |
| You decide | 你来决定。 | |

**User's choice:** Map<name, AgentState>（推荐）

---

## WebSocket 连接策略

### 连接建立时机

| Option | Description | Selected |
|--------|-------------|----------|
| 页面加载自动连接（推荐） | 页面加载时立即连接 ws://localhost:8765。用户无感知。适合 MVP。 | ✓ |
| 手动连接 | 显示「连接」按钮。更可控但多一步操作。 | |
| You decide | 你来决定。 | |

**User's choice:** 页面加载自动连接（推荐）

### 重连参数

| Option | Description | Selected |
|--------|-------------|----------|
| 1s 起步 ×2 上限 30s（推荐） | 初始 1 秒，每次加倍，最大 30 秒，最多 10 次。典型指数退避。 | ✓ |
| 2s 起步 ×2 上限 60s 无限重试 | 更保守但无限重试可能永远卡住。 | |
| You decide | 你来决定具体参数。 | |

**User's choice:** 1s 起步 ×2 上限 30s（推荐）

### 连接状态指示器位置

| Option | Description | Selected |
|--------|-------------|----------|
| 顶部状态栏小圆点（推荐） | 页面顶部横条，左侧小圆点（绿/黄/红）+ 文字。不占太多空间。 | ✓ |
| 面板内嵌 | 放在 Team 控制按钮旁。更贴近操作区但可能被忽略。 | |
| You decide | 你来决定。 | |

**User's choice:** 顶部状态栏小圆点（推荐）

---

## 配置表单与交互流程

### 创建 Agent 表单布局

| Option | Description | Selected |
|--------|-------------|----------|
| 简洁三字段 | Name、Role、System Prompt 纵向排列。每字段上方有 label。简洁够用。 | |
| 折叠式表单 | Role 和 System Prompt 用折叠/展开，默认只显示 Name 和 Role。更紧凑。 | ✓ |
| You decide | 你来决定。 | |

**User's choice:** 折叠式表单

### 启动/停止按钮位置

| Option | Description | Selected |
|--------|-------------|----------|
| 表单下方双按钮（推荐） | 配置表单下方放启动（terracotta）和停止（error crimson）按钮，状态联动。 | ✓ |
| Agent 列表内嵌按钮 | 每个 agent 旁有独立按钮。MVP 单 agent 没必要。 | |
| You decide | 你来决定。 | |

**User's choice:** 表单下方双按钮（推荐）

### Agent 状态灯视觉设计

| Option | Description | Selected |
|--------|-------------|----------|
| CSS 彩色圆点（推荐） | 小圆点 8×8px：绿色=idle，蓝色=thinking，橙色=tool_call，灰色=shutdown。用 CSS 实现。 | ✓ |
| 动画圆点 | 有呼吸/闪烁动画。更生动但增加复杂度。 | |
| 文字标签 | 文字显示状态。更明确但占空间。 | |

**User's choice:** CSS 彩色圆点（推荐）

---

## Claude's Discretion

- 组件文件命名和具体拆分方式（哪些放 agent/、layout/、ui/）
- CSS 圆点的具体颜色值（参考 DESIGN.md 暖色系统）
- 事件日志条目的显示格式
- 折叠式表单的展开/收起动画实现方式
- 连接状态指示器的具体样式细节
- useReducer 的 action type 命名和 state 类型定义

## Deferred Ideas

None — discussion stayed within phase scope
