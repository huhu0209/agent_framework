# Phase 10: Frontend Canvas 渲染 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 10-Frontend Canvas 渲染
**Areas discussed:** 场景美术风格, 帧动画实现方案, Canvas 页面布局, 开发预览体验

---

## 场景美术风格

| Option | Description | Selected |
|--------|-------------|----------|
| 简约几何 | 基本几何形状+DESIGN.md 暖色调，匹配 placeholder 精灵 | |
| 扁平插画风格 | 圆角矩形+渐变色块，更有表现力 | |
| 像素风 | 8-bit 像素画，匹配 32×32 精灵 | |

**User's choice:** 期望精美场景（电脑、工位、办公室、马桶、饮水机、茶水间、会议室），后确认 MVP 最小化只画必要元素（2 工位 + 茶水间 + 门口），其他留 v0.0.4+

**Notes:** 用户提供了自己的框架表格，确认了 4 帧动画（站/走路/打字/喝水）和状态映射。用户方案覆盖了 ROADMAP 原文的映射关系。

### 状态映射确认

| Option | Description | Selected |
|--------|-------------|----------|
| 用户表格方案 | idle→喝水, thinking→站+气泡, tool_call→打字, 走路过渡 | ✓ |
| ROADMAP 原文 | idle→站立, thinking→打字, tool_call→喝水 | |

---

## 帧动画实现方案

| Option | Description | Selected |
|--------|-------------|----------|
| 程序化几何动画 | PixiJS ticker 更新形状位置/旋转/缩放 | ✓ |
| Canvas 预渲染 sprite sheet | Canvas API 预画帧，AnimatedSprite 播放 | |
| PixiJS Graphics + Tween 库 | 第三方 tween 库做插值，多一个依赖 | |

**User's choice:** 程序化几何动画

### 精灵尺寸

| Option | Description | Selected |
|--------|-------------|----------|
| 32×32 | 可见性好，细节空间更大 | ✓ |
| 16×16 | 更小巧精致 | |

---

## Canvas 页面布局

| Option | Description | Selected |
|--------|-------------|----------|
| 左 Canvas + 右面板 | 左侧办公室场景，右侧控制面板+事件日志 | ✓ |
| 全屏 Canvas + 浮动面板 | Canvas 占满，面板叠加 overlay | |
| 上 Canvas + 下面板 | 上方场景，下方控制面板 | |

**User's choice:** 左 Canvas + 右面板

### Canvas 尺寸策略

| Option | Description | Selected |
|--------|-------------|----------|
| 固定 4:3 | 如 800×600，布局简单可预测 | ✓ |
| 响应式自适应 | 跟随窗口大小，需处理不同宽高比 | |

---

## 开发预览体验

| Option | Description | Selected |
|--------|-------------|----------|
| 独立 HTML 预览页 | 单独 preview.html，不依赖 React | ✓ |
| 集成到 React App | 在 Vite React dev server 中开发 | |

---

## Claude's Discretion

- 场景元素具体几何形状设计
- 点位精确坐标和间距
- 程序化动画参数
- Canvas 内部 3 层 Container 实现细节
- 颜色方案（参考 DESIGN.md）
- 思考气泡效果实现

## Deferred Ideas

- 更多办公室元素（电脑细节、饮水机、会议室、马桶） — v0.0.4+
- 响应式 Canvas — v0.0.4+
- 真实美术资源 — v0.0.4+
- 多动物形象 — v0.0.4+ (RNDR-F01)
