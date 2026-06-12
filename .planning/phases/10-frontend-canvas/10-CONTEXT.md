# Phase 10: Frontend Canvas 渲染 - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

PixiJS v8 办公室场景渲染层 — 猫精灵 + 4 个点位 + 4 种程序化帧动画 + 线性插值移动系统。
纯前端 Canvas 渲染模块，不依赖 React 数据层。Phase 11 通过 React ref 桥接 VizEvent 数据。

</domain>

<decisions>
## Implementation Decisions

### 场景视觉与布局
- **D-01:** 场景最小化 — 只画 4 个点位对应元素（2 工位 + 茶水间 + 门口），其他办公室元素（会议室、马桶等）留 v0.0.4+
- **D-02:** 几何简笔画风格 — 场景元素用简洁几何形状，匹配 placeholder 猫精灵风格
- **D-03:** Canvas 固定 4:3 比例（如 800×600），不随窗口自适应。Phase 11 决定容器大小

### 状态→动画→点位映射（用户方案，覆盖 ROADMAP 原文）
- **D-04:** 状态映射关系：
  - idle → 喝水动画（茶水间点位）
  - thinking → 站+气泡动画（工位点位）
  - tool_call → 打字动画（工位点位）
  - 移动中 → 走路动画（点位间过渡）
  - shutdown → 移动到门口 + 消失

### 帧动画方案
- **D-05:** 4 种帧动画：站、走路、打字、喝水。新增"走路"帧用于点位间过渡
- **D-06:** 程序化几何动画 — 用 PixiJS ticker 更新形状的位置/旋转/缩放模拟帧动画，不用 sprite sheet
- **D-07:** 猫精灵 32×32 像素，圆形身体 + 三角形耳朵

### 页面布局与开发
- **D-08:** 最终布局：左侧 Canvas + 右侧 React 面板（Phase 11 实现 React 部分）
- **D-09:** 开发预览用独立 HTML 页面（preview.html），不依赖 React，Phase 10 代码导出纯 JS/TS module

### Claude's Discretion
- 场景元素的具体几何形状设计（桌子、茶水间、门口的几何组合）
- 4 个点位的精确坐标和间距
- 程序化动画的具体参数（弹跳幅度、走路频率、打字速度等）
- Canvas 内部 3 层 Container（背景层/agent 层/效果层）的具体实现
- 颜色方案：参考 DESIGN.md 暖色调（parchment 背景、terracotta 强调色）
- 思考气泡效果的实现方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与规划
- `.planning/REQUIREMENTS.md` — RNDR-01~07 需求定义（Canvas 渲染层所有需求）
- `.planning/ROADMAP.md` — Phase 10 目标、成功标准、3 个 plan 分解

### 事件模型（Phase 9 已实现）
- `.planning/phases/09-backend/09-CONTEXT.md` — VizEvent 数据模型（D-06: event types = idle/thinking/tool_call/done/error/shutdown）
- `framework/agent_framework/viz/viz_event.py` — VizEvent Pydantic 模型实现

### 设计规范
- `DESIGN.md` — HTML 设计规范（parchment 暖色背景 #f5f4ed、terracotta 品牌色 #c96442）

### 前端基础设施
- `frontend/package.json` — 现有前端依赖（React 19, Vite 8, Tailwind 4）
- `frontend/vite.config.ts` — Vite 配置（React + Tailwind 插件）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 前端脚手架已就绪：Vite 8 + React 19 + TypeScript 6 + Tailwind 4
- frontend/src/ 目录结构已有 components/, hooks/, pages/ 等目录
- DESIGN.md 定义了暖色调设计系统（parchment 背景、terracotta 强调色、warm-neutral palette）

### Established Patterns
- 前端用 TypeScript ESM 模块（"type": "module"）
- PixiJS v8 需要新增为 npm 依赖（`pixi.js`）
- 组件放在 frontend/src/components/{category}/ 下
- CSS 用 Tailwind 4 utility classes

### Integration Points
- Phase 11 通过 React ref 将 VizEvent 数据桥接到 PixiJS（CONC-03 需求）
- Canvas 模块需要导出清晰 API：init(container, options) / updateState(vizEvent) / destroy()
- PixiJS Application 需要接收一个 HTML 容器元素
- VizEvent type 枚举（idle/thinking/tool_call/done/error/shutdown）是数据接口契约

</code_context>

<specifics>
## Specific Ideas

- 猫精灵 4 种程序化动画：站（thinking 时叠加气泡效果）、走路（点位间过渡）、打字（tool_call）、喝水（idle）
- 走路动画在精灵从一点位移动到另一点位期间播放，到达后切换到目标状态动画
- 站动画是 thinking 的基础姿态，额外叠加一个半透明椭圆+文字的思考气泡
- 场景只有 4 个点位但应有"办公室"氛围感，通过颜色和几何组合传达

</specifics>

<deferred>
## Deferred Ideas

- 更多办公室元素（电脑细节、饮水机、会议室、马桶等） — v0.0.4+
- 响应式 Canvas 自适应窗口大小 — v0.0.4+
- 真实像素美术资源替换 placeholder 几何图形 — v0.0.4+
- 多动物形象选择（猫/狗/兔/熊/鸟） — v0.0.4+ (RNDR-F01)

</deferred>

---

*Phase: 10-Frontend Canvas 渲染*
*Context gathered: 2026-05-30*
