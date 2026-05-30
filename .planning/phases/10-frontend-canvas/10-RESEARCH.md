# Phase 10: Frontend Canvas 渲染 - Research

**Researched:** 2026-05-30
**Domain:** PixiJS v8 Canvas 渲染、程序化几何动画、线性插值移动系统
**Confidence:** HIGH

## Summary

Phase 10 的核心任务是在浏览器中用 PixiJS v8 渲染一个简笔画风格的办公室场景，包含一只几何猫咪精灵、4 个固定点位和 4 种程序化帧动画。这是一个纯前端渲染模块，不依赖 React 数据层。Phase 11 通过 React ref 桥接 VizEvent 数据。

PixiJS v8 相比 v7 有重大 API 变更：`Application` 初始化变为异步（`app.init()` 代替构造函数参数）、`app.view` 改为 `app.canvas`、Graphics API 从 `beginFill()/drawCircle()` 改为先构建形状再 `.fill()/.stroke()` 的模式、`DisplayObject` 被移除，`Container` 成为基类。这些变化意味着所有代码必须基于 v8 API 编写。

关键技术决策已通过 CONTEXT.md 锁定：程序化几何动画（不用 sprite sheet）、32x32 像素猫咪、4:3 固定 Canvas、独立 HTML 预览页面。本研究的重点是为这些决策提供准确的 API 参考和实现模式。

**Primary recommendation:** 使用 PixiJS v8 (8.18.1) 的 Graphics API 构建程序化精灵，Ticker 驱动帧动画，Container 三层架构（背景/agent/效果），lerp 实现平滑移动。模块导出 `init()/updateState()/destroy()` API 供 Phase 11 桥接。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 场景最小化 — 只画 4 个点位对应元素（2 工位 + 茶水间 + 门口），其他办公室元素留 v0.0.4+
- **D-02:** 几何简笔画风格 — 场景元素用简洁几何形状，匹配 placeholder 猫精灵风格
- **D-03:** Canvas 固定 4:3 比例（如 800x600），不随窗口自适应。Phase 11 决定容器大小
- **D-04:** 状态映射关系：
  - idle -> 喝水动画（茶水间点位）
  - thinking -> 站+气泡动画（工位点位）
  - tool_call -> 打字动画（工位点位）
  - 移动中 -> 走路动画（点位间过渡）
  - shutdown -> 移动到门口 + 消失
- **D-05:** 4 种帧动画：站、走路、打字、喝水。新增"走路"帧用于点位间过渡
- **D-06:** 程序化几何动画 — 用 PixiJS ticker 更新形状的位置/旋转/缩放模拟帧动画，不用 sprite sheet
- **D-07:** 猫精灵 32x32 像素，圆形身体 + 三角形耳朵
- **D-08:** 最终布局：左侧 Canvas + 右侧 React 面板（Phase 11 实现 React 部分）
- **D-09:** 开发预览用独立 HTML 页面（preview.html），不依赖 React，Phase 10 代码导出纯 JS/TS module

### Claude's Discretion
- 场景元素的具体几何形状设计（桌子、茶水间、门口的几何组合）
- 4 个点位的精确坐标和间距
- 程序化动画的具体参数（弹跳幅度、走路频率、打字速度等）
- Canvas 内部 3 层 Container（背景层/agent 层/效果层）的具体实现
- 颜色方案：参考 DESIGN.md 暖色调（parchment 背景、terracotta 强调色）
- 思考气泡效果的实现方式

### Deferred Ideas (OUT OF SCOPE)
- 更多办公室元素（电脑细节、饮水机、会议室、马桶等） — v0.0.4+
- 响应式 Canvas 自适应窗口大小 — v0.0.4+
- 真实像素美术资源替换 placeholder 几何图形 — v0.0.4+
- 多动物形象选择（猫/狗/兔/熊/鸟） — v0.0.4+ (RNDR-F01)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RNDR-01 | PixiJS v8 应用初始化，包含背景层/agent层/效果层三个 Container | v8 Application.init() 异步初始化 + Container 三层架构模式 |
| RNDR-02 | 办公室场景包含 4 个固定点位（2 个工位 + 茶水间 + 门口） | Graphics API 绘制场景元素 + 点位坐标常量定义 |
| RNDR-03 | 猫精灵使用 placeholder 几何图形（圆形+三角形耳朵），32x32 像素 | Graphics.circle() + Graphics.poly() 绘制猫咪部件 |
| RNDR-04 | 猫精灵支持 3 种帧动画（站立/打字/喝水），对应 idle/thinking/tool_call 状态 | Ticker 驱动帧动画 + GraphicsContext 上下文切换模式 |
| RNDR-05 | Agent 状态变化时，动物自动移动到对应场景点位（线性插值平滑移动） | lerp 公式 + Ticker 每帧更新位置 + 移动完成检测 |
| RNDR-06 | 动物到达目标点位后播放对应状态帧动画 | 状态机模式：移动完成 -> 切换到目标状态动画 |
| RNDR-07 | Agent shutdown 时动物移动到门口并消失 | 移动到门口点位 + alpha 渐变消失 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PixiJS Application 初始化与 Canvas 管理 | Browser / Client | - | 纯浏览器端 Canvas 渲染，无服务端参与 |
| 场景绘制（背景、点位元素） | Browser / Client | - | Graphics API 在 Canvas 上绘制几何形状 |
| 精灵渲染与帧动画 | Browser / Client | - | Ticker 驱动的程序化动画，纯客户端计算 |
| 线性插值移动系统 | Browser / Client | - | lerp 计算在每帧 Ticker 回调中执行 |
| VizEvent 数据接口 | API / Backend (定义) | Browser / Client (消费) | Phase 9 已定义 Python 模型，Phase 10 定义 TS 接口镜像 |
| Preview HTML 页面 | CDN / Static | - | 独立 HTML 文件，不经过 React 构建管线 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pixi.js | 8.18.1 | 2D Canvas/WebGPU 渲染引擎 | 项目已选定（RNDR 需求明确指定 PixiJS v8）[VERIFIED: npm registry] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typescript | ~6.0.2 | 类型安全 | 项目已配置，pixi.js v8 原生 TS 类型 [VERIFIED: npm registry] |
| vite | ^8.0.12 | 构建工具 + 开发服务器 | 项目已配置，pixi.js 通过 Vite ESM 导入 [VERIFIED: npm registry] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pixi.js (完整包) | pixi.js 自定义构建 | 完整包含所有扩展，初始开发简单；自定义构建可减小体积但对 MVP 不必要 |
| @pixi/react | 原生 pixi.js API | @pixi/react 尚在迁移到 v8 过程中（官方迁移指南确认），且 D-09 要求纯 TS module 不依赖 React |

**Installation:**
```bash
cd frontend && npm install pixi.js
```

**Version verification:**
```
pixi.js: 8.18.1 (npm registry, 2026-05-05 latest dev build)
TypeScript: ~6.0.2 (已在 package.json)
Vite: ^8.0.12 (已在 package.json)
```

## Package Legitimacy Audit

> slopcheck 不可用，所有包标记为 [ASSUMED]。

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pixi.js | npm | ~2+ years (v8 发布于 2024) | 数百万/周 | github.com/pixijs/pixijs | N/A | [ASSUMED] — 著名开源项目，但未经 slopcheck 验证 |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. pixi.js 是成熟的 2D 渲染库（GitHub 43k+ stars），风险极低。planner 可视情况跳过 checkpoint。*

## Architecture Patterns

### System Architecture Diagram

```
                  preview.html (Phase 10 开发预览)
                       |
                       v
              +------------------+
              | CanvasRenderer   |  <- init(container, options)
              | (导出模块)        |  <- updateState(vizEvent)
              |                  |  <- destroy()
              +--------+---------+
                       |
         +-------------+-------------+
         |             |             |
    +----+----+  +-----+----+  +----+-----+
    | 背景层  |  | Agent层  |  | 效果层   |
    |Container|  |Container |  |Container |
    +---------+  +-----+----+  +----------+
    | 场景元素 |        |        | 气泡效果 |
    | 点位标记 |  +-----+----+   | 状态指示 |
    | 装饰    |  | CatSprite |  +----------+
    +---------+  | (几何猫咪) |
                 | 动画状态机 |
                 | 移动系统   |
                 +------------+
                       |
                  +-----+-----+
                  |   Ticker   |  <- 每帧驱动
                  | (动画循环)  |
                  +-----------+
```

数据流：外部调用 `updateState(vizEvent)` -> 状态机解析事件类型 -> 如果需要移动：启动 lerp 移动（走路动画）-> 到达后切换目标动画 -> 如果已是目标点位：直接切换动画

### Recommended Project Structure
```
frontend/src/
├── canvas/                    <- Phase 10 新增目录
│   ├── index.ts              <- 模块入口，导出 init/updateState/destroy
│   ├── types.ts              <- VizEvent TS 接口 + 动画状态枚举
│   ├── renderer.ts           <- PixiJS Application 初始化 + 3 层 Container
│   ├── scene.ts              <- 办公室场景绘制（背景层元素）
│   ├── cat-sprite.ts         <- 猫精灵（几何绘制 + 4 种动画）
│   ├── animations.ts         <- 程序化帧动画定义（参数 + 状态机）
│   ├── movement.ts           <- lerp 移动系统
│   └── constants.ts          <- 点位坐标、颜色、尺寸常量
├── components/               <- 已存在，Phase 10 不涉及
├── hooks/                    <- 已存在，Phase 10 不涉及
├── pages/                    <- 已存在，Phase 10 不涉及
└── types/                    <- 已存在，Phase 10 在 canvas/types.ts 定义独立类型
frontend/
├── preview.html              <- Phase 10 开发预览页面（根目录）
```

### Pattern 1: PixiJS v8 Application 初始化（异步）

**What:** PixiJS v8 的 Application 初始化是异步的，必须 await。
**When to use:** 模块初始化时调用。

```typescript
// Source: [CITED: pixijs.com/8.x/guides/migrations/v8]
import { Application, Container } from 'pixi.js';

const app = new Application();
await app.init({
  width: 800,
  height: 600,
  background: 0xf5f4ed,  // Parchment 色背景 (v8: background 取代 backgroundColor)
  antialias: true,
  resolution: window.devicePixelRatio || 1,
  autoDensity: true,
});

// v8: app.canvas 取代 app.view
container.appendChild(app.canvas);

// 三层 Container 架构
const backgroundLayer = new Container();
backgroundLayer.label = 'background';  // v8: label 取代 name
const agentLayer = new Container();
agentLayer.label = 'agent';
const effectsLayer = new Container();
effectsLayer.label = 'effects';

app.stage.addChild(backgroundLayer, agentLayer, effectsLayer);
```

### Pattern 2: v8 Graphics API（先构建形状再填充）

**What:** PixiJS v8 的 Graphics API 从 "beginFill then draw" 改为 "draw then fill/stroke"。
**When to use:** 绘制所有几何形状（猫咪、场景元素）。

```typescript
// Source: [CITED: pixijs.com/8.x/guides/components/scene-objects/graphics]
import { Graphics } from 'pixi.js';

// v7 旧写法（不要用）:
// new Graphics().beginFill(0xff0000).drawCircle(50, 50, 25).endFill()

// v8 新写法:
const body = new Graphics()
  .circle(0, 0, 12)        // 圆形身体，半径 12px（32x32 精灵内）
  .fill(0xc96442);          // Terracotta 品牌色

const ear1 = new Graphics()
  .poly([0, 0, 5, -8, -5, -8])  // 三角形耳朵 (v8: poly 取代 drawPolygon)
  .fill(0xc96442);

// 描边
const outline = new Graphics()
  .circle(0, 0, 14)
  .stroke({ width: 1, color: 0x141413 });  // Near Black 描边
```

### Pattern 3: GraphicsContext 上下文切换（帧动画核心）

**What:** 预构建多个 GraphicsContext，通过切换 context 实现帧动画。
**When to use:** 4 种猫咪动画的帧切换。

```typescript
// Source: [CITED: pixijs.com/8.x/guides/components/scene-objects/graphics]
import { Graphics, GraphicsContext } from 'pixi.js';

// 预构建每帧的 GraphicsContext
const standFrame1 = new GraphicsContext()
  .circle(0, 0, 12).fill(0xc96442)
  .poly([-8, -8, -3, -16, 2, -8]).fill(0xc96442)   // 左耳
  .poly([2, -8, 7, -16, 12, -8]).fill(0xc96442);    // 右耳

const standFrame2 = new GraphicsContext()
  .circle(0, 0, 12).fill(0xc96442)
  .poly([-8, -7, -3, -15, 2, -7]).fill(0xc96442)
  .poly([2, -7, 7, -15, 12, -7]).fill(0xc96442);

const cat = new Graphics(standFrame1);

// 切换帧（非常高效）
function setFrame(frame: GraphicsContext) {
  cat.context = frame;
}
```

### Pattern 4: Ticker 驱动动画循环

**What:** 使用 PixiJS v8 的 Ticker 驱动每帧更新。
**When to use:** 帧动画播放、位置插值移动。

```typescript
// Source: [CITED: pixijs.com/8.x/guides/components/ticker]
import { Ticker } from 'pixi.js';

// v8 重要变化: Ticker 回调参数是 Ticker 实例，不是 deltaTime
// v7 旧写法: ticker.add((dt) => { ... })
// v8 新写法:
app.ticker.add((ticker) => {
  // ticker.deltaTime 是帧间时间倍数（60fps 基准）
  // ticker.elapsedMS 是毫秒数
  const dt = ticker.deltaTime;

  // 更新精灵位置
  sprite.x += velocityX * dt;
  sprite.y += velocityY * dt;
});

// 也可以用 app.ticker 代替 Ticker.shared
// app.ticker 在 app.init() 后自动可用
```

### Pattern 5: lerp 线性插值移动

**What:** 使用线性插值平滑移动精灵到目标点位。
**When to use:** Agent 状态变化时精灵需要移动到新点位。

```typescript
function lerp(current: number, target: number, speed: number): number {
  return current + (target - current) * speed;
}

// 在 Ticker 回调中：
let isMoving = false;
let targetX = 0;
let targetY = 0;
const MOVE_SPEED = 0.05; // 每帧插值比例

app.ticker.add((ticker) => {
  if (!isMoving) return;

  const dt = ticker.deltaTime;
  cat.x = lerp(cat.x, targetX, MOVE_SPEED * dt);
  cat.y = lerp(cat.y, targetY, MOVE_SPEED * dt);

  // 到达检测
  const distance = Math.hypot(targetX - cat.x, targetY - cat.y);
  if (distance < 1) {
    cat.x = targetX;
    cat.y = targetY;
    isMoving = false;
    onArrived();  // 到达后切换到目标状态动画
  }
});
```

### Pattern 6: 模块 API 边界设计

**What:** Canvas 模块导出清晰的 init/updateState/destroy API。
**When to use:** Phase 11 通过 React ref 桥接数据。

```typescript
// canvas/index.ts
import { VizEvent, AnimationState } from './types';
import { createRenderer } from './renderer';

export async function init(container: HTMLElement, options?: { width?: number; height?: number }) {
  // 初始化 PixiJS Application + 场景
}

export function updateState(event: VizEvent): void {
  // 解析 VizEvent.type -> 触发移动/动画切换
}

export function destroy(): void {
  // 销毁 Application，清理资源
}
```

### Pattern 7: Preview HTML 页面

**What:** 独立 HTML 页面用于开发预览，不依赖 React。
**When to use:** Phase 10 开发期间测试 Canvas 渲染。

```html
<!-- frontend/preview.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Canvas Preview - Agent Framework</title>
  <style>
    body { margin: 0; display: flex; justify-content: center; align-items: center;
           min-height: 100vh; background: #f5f4ed; }
    canvas { border: 1px solid #e8e6dc; }
  </style>
</head>
<body>
  <div id="canvas-container"></div>
  <script type="module">
    import { init, updateState, destroy } from './src/canvas/index.ts';

    const container = document.getElementById('canvas-container');
    await init(container);

    // 测试各种状态
    updateState({ type: 'idle', agent: 'cat', payload: {}, timestamp: Date.now() / 1000 });
    setTimeout(() => updateState({ type: 'thinking', agent: 'cat', payload: {}, timestamp: Date.now() / 1000 }), 3000);
    setTimeout(() => updateState({ type: 'tool_call', agent: 'cat', payload: {}, timestamp: Date.now() / 1000 }), 6000);
    setTimeout(() => updateState({ type: 'shutdown', agent: 'cat', payload: {}, timestamp: Date.now() / 1000 }), 9000);
  </script>
</body>
</html>
```

### Anti-Patterns to Avoid
- **v7 构造函数初始化:** `new Application({ width, height })` 在 v8 不工作。必须用 `app.init()` 异步初始化 [CITED: pixijs.com/8.x/guides/migrations/v8]
- **beginFill/endFill 模式:** v7 的 `beginFill().drawCircle().endFill()` 模式已废弃。v8 是 `circle().fill()` [CITED: pixijs.com/8.x/guides/migrations/v8]
- **app.view 引用:** v8 中改为 `app.canvas` [CITED: pixijs.com/8.x/guides/migrations/v8]
- **DisplayObject 基类:** v8 移除了 `DisplayObject`，`Container` 是所有场景对象的基类 [CITED: pixijs.com/8.x/guides/migrations/v8]
- **Graphics 子节点:** v8 中 Graphics（叶节点）不能添加子节点。需要用 Container 包裹多个 Graphics [CITED: pixijs.com/8.x/guides/migrations/v8]
- **每帧重建 Graphics:** 性能极差。应预构建 GraphicsContext，通过 context 切换实现帧动画 [CITED: pixijs.com/8.x/guides/components/scene-objects/graphics]
- **Ticker 回调参数误解:** v8 回调参数是 `Ticker` 实例（不是 `number`），需要 `ticker.deltaTime` 获取 delta [CITED: pixijs.com/8.x/guides/components/ticker]
- **backgroundColor 选项:** v8 改为 `background`（单数形式） [CITED: pixijs.com/8.x/guides/migrations/v8]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Canvas 渲染循环 | 自己管理 requestAnimationFrame | PixiJS Application.ticker | PixiJS 处理 WebGPU/WebGL 自动降级、帧率控制、设备像素比 |
| 2D 几何渲染 | Canvas 2D API 手动绘制 | PixiJS Graphics API | Graphics 自动批处理、GPU 加速、支持 WebGPU |
| 动画时间管理 | 手动计算 deltaTime | Ticker.deltaTime | Ticker 提供帧率控制、优先级排序、暂停恢复 |
| 场景图管理 | 自己实现父子关系树 | Container | Container 提供变换继承、子节点管理、排序、缓存 |

**Key insight:** PixiJS v8 的 GraphicsContext 预构建 + context 切换模式是程序化帧动画的最佳实践。每帧重建 Graphics 对象会导致严重的 GPU 批处理中断。

## Common Pitfalls

### Pitfall 1: v7 到 v8 的 API 混用
**What goes wrong:** 使用 v7 的 `new Application({ ... })` 同步构造，或 `beginFill()` / `drawCircle()` 调用方式。
**Why it happens:** 大量网络教程和 StackOverflow 回答仍基于 v7。
**How to avoid:** 严格使用 v8 迁移指南作为参考。所有 Graphics 调用使用 "先形状后样式" 模式。
**Warning signs:** TypeScript 编译错误或运行时 "is not a function" 错误。

### Pitfall 2: Graphics 作为 Container 使用
**What goes wrong:** 尝试给 Graphics 对象 addChild()，v8 中叶节点（Graphics/Sprite）不能有子节点。
**Why it happens:** v7 允许 Sprite 等叶节点添加子节点。
**How to avoid:** 用 Container 包裹多个 Graphics 对象。例如猫咪精灵用一个 Container 包裹 body Graphics + ears Graphics + eyes Graphics。
**Warning signs:** `addChild is not a function` 或子节点不显示。

### Pitfall 3: Ticker 回调参数类型变化
**What goes wrong:** 写 `ticker.add((dt) => ...)` 但 `dt` 实际是 Ticker 对象而非数字。
**Why it happens:** v7 回调参数是 deltaTime 数字，v8 改为 Ticker 实例。
**How to avoid:** 使用 `ticker.add((ticker) => { const dt = ticker.deltaTime; })`。
**Warning signs:** 位置/动画值变成 NaN 或极大数字。

### Pitfall 4: lerp 到达检测不精确
**What goes wrong:** lerp 永远不完全到达目标（浮点精度），导致动画卡在"移动中"状态。
**Why it happens:** lerp 每帧乘以比例，理论上无限逼近但永远不到达。
**How to avoid:** 设置距离阈值（如 < 1px）时直接设为目标值，并标记移动完成。
**Warning signs:** 精灵在目标点附近微颤或动画状态卡在 walking。

### Pitfall 5: 忘记 await app.init()
**What goes wrong:** `new Application()` 后直接访问 `app.canvas` 或 `app.stage`，得到 undefined。
**Why it happens:** v8 的 Application 构造函数不再接受参数，init() 是异步的（因为 WebGPU 需要异步初始化）。
**How to avoid:** 始终在 async 函数中 `await app.init()` 后再操作。
**Warning signs:** "Cannot read property 'appendChild' of undefined" 或 app.canvas 为 undefined。

### Pitfall 6: preview.html 中 Vite 模块路径
**What goes wrong:** `<script type="module" src="./src/canvas/index.ts">` 无法在 Vite 开发服务器外直接打开。
**Why it happens:** 浏览器不直接支持 TS 模块导入，需要 Vite 开发服务器编译。
**How to avoid:** preview.html 必须通过 `npx vite` 或 `npm run dev` 访问，不能直接 file:// 打开。或将 preview.html 放在 frontend/ 根目录让 Vite 处理。
**Warning signs:** 浏览器控制台 "Failed to load module" 错误。

## Code Examples

### PixiJS v8 完整初始化示例
```typescript
// Source: [CITED: pixijs.com/8.x/guides/migrations/v8] + [CITED: pixijs.com/8.x/guides/components/scene-objects/container]
import { Application, Container, Graphics } from 'pixi.js';

export async function createCanvasRenderer(container: HTMLElement) {
  const app = new Application();
  await app.init({
    width: 800,
    height: 600,
    background: 0xf5f4ed,  // Parchment
    antialias: true,
    resolution: window.devicePixelRatio || 1,
    autoDensity: true,
  });

  container.appendChild(app.canvas);

  // 三层 Container
  const backgroundLayer = new Container({ label: 'background' });
  const agentLayer = new Container({ label: 'agent' });
  const effectsLayer = new Container({ label: 'effects' });
  app.stage.addChild(backgroundLayer, agentLayer, effectsLayer);

  return { app, backgroundLayer, agentLayer, effectsLayer };
}
```

### 几何猫咪绘制示例
```typescript
// Source: [CITED: pixijs.com/8.x/guides/components/scene-objects/graphics]
import { Container, Graphics, GraphicsContext } from 'pixi.js';

// 猫咪由 Container 包裹多个 Graphics 叶节点
function createCatSprite(): Container {
  const cat = new Container({ label: 'cat' });

  // 身体 — 圆形
  const body = new Graphics()
    .circle(0, 2, 10)
    .fill(0xc96442);  // Terracotta

  // 左耳 — 三角形
  const leftEar = new Graphics()
    .poly([-8, -4, -5, -12, -1, -4])
    .fill(0xc96442);

  // 右耳 — 三角形
  const rightEar = new Graphics()
    .poly([1, -4, 5, -12, 8, -4])
    .fill(0xc96442);

  // 眼睛 — 两个小圆
  const eyes = new Graphics()
    .circle(-4, 0, 2).fill(0x141413)  // Near Black
    .circle(4, 0, 2).fill(0x141413);

  cat.addChild(body, leftEar, rightEar, eyes);
  return cat;
}
```

### 程序化帧动画示例（走路）
```typescript
// Source: [CITED: pixijs.com/8.x/guides/components/scene-objects/graphics] + [CITED: pixijs.com/8.x/guides/components/ticker]
import { Container, Graphics } from 'pixi.js';

// 走路动画：通过 Ticker 周期性调整腿部/身体的 y 偏移和旋转
function startWalkingAnimation(cat: Container, app: Application) {
  let frame = 0;
  const WALK_CYCLE_SPEED = 0.15; // 控制动画速度

  const tickerCallback = (ticker: { deltaTime: number }) => {
    frame += WALK_CYCLE_SPEED * ticker.deltaTime;
    const bounce = Math.sin(frame * Math.PI) * 2; // 上下弹跳
    const tilt = Math.sin(frame * Math.PI) * 0.05; // 左右微倾

    cat.y += bounce * 0.3;   // 弹跳效果
    cat.rotation = tilt;      // 身体微倾
  };

  app.ticker.add(tickerCallback);
  return () => app.ticker.remove(tickerCallback); // 返回清理函数
}
```

### lerp 移动系统完整示例
```typescript
// Source: 线性插值标准公式
import { Container } from 'pixi.js';

interface MovementState {
  isMoving: boolean;
  targetX: number;
  targetY: number;
  onArrive?: () => void;
}

function createMovementSystem(cat: Container, app: Application) {
  const state: MovementState = { isMoving: false, targetX: 0, targetY: 0 };
  const MOVE_SPEED = 0.06;
  const ARRIVAL_THRESHOLD = 1.0;

  const tickerCallback = (ticker: { deltaTime: number }) => {
    if (!state.isMoving) return;

    const dt = ticker.deltaTime;
    cat.x += (state.targetX - cat.x) * MOVE_SPEED * dt;
    cat.y += (state.targetY - cat.y) * MOVE_SPEED * dt;

    const distance = Math.hypot(state.targetX - cat.x, state.targetY - cat.y);
    if (distance < ARRIVAL_THRESHOLD) {
      cat.x = state.targetX;
      cat.y = state.targetY;
      state.isMoving = false;
      state.onArrive?.();
    }
  };

  app.ticker.add(tickerCallback);

  return {
    moveTo(x: number, y: number, onArrive?: () => void) {
      state.targetX = x;
      state.targetY = y;
      state.onArrive = onArrive;
      state.isMoving = true;
    },
    dispose() {
      app.ticker.remove(tickerCallback);
    },
  };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PixiJS v7 同步 Application 构造 | v8 异步 init() | PixiJS v8 (2024) | 所有初始化代码必须 async |
| beginFill/drawX/endFill | 先 shape 后 fill/stroke | PixiJS v8 (2024) | Graphics API 完全重写 |
| app.view (HTMLCanvasElement) | app.canvas | PixiJS v8 (2024) | 属性重命名 |
| DisplayObject 基类 | Container 是唯一基类 | PixiJS v8 (2024) | 叶节点不能有子节点 |
| Sprite 子节点 | Container 包裹叶节点 | PixiJS v8 (2024) | 必须用 Container 组织层次 |
| container.name | container.label | PixiJS v8 (2024) | 属性重命名 |
| GraphicsGeometry | GraphicsContext（可共享） | PixiJS v8 (2024) | 帧动画用 context 切换 |

**Deprecated/outdated:**
- `beginFill()/endFill()`: v8 中用 `.fill()` 替代 [CITED: pixijs.com/8.x/guides/migrations/v8]
- `lineStyle()`: v8 中用 `.stroke()` 替代 [CITED: pixijs.com/8.x/guides/migrations/v8]
- `drawCircle/drawRect/drawPolygon`: v8 中简化为 `.circle()/.rect()/.poly()` [CITED: pixijs.com/8.x/guides/migrations/v8]
- `@pixi/react` (v7 版本): 正在迁移到 v8，不建议 MVP 使用 [CITED: pixijs.com/8.x/guides/migrations/v8]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pixi.js v8.18.1 是最新稳定版且无已知破坏性 bug | Standard Stack | 可能需要锁定到特定小版本 |
| A2 | pixi.js v8 原生包含 TypeScript 类型定义 | Standard Stack | 如果不包含，需要额外安装 @types |
| A3 | preview.html 可以通过 Vite 开发服务器加载 TS 模块 | Pattern 7 | 可能需要额外 Vite 配置 |
| A4 | GraphicsContext 切换足够高效实现 4 帧动画 | Pattern 3 | 如果性能不够，需要备选方案 |
| A5 | Vite 8 能正确打包 pixi.js 依赖 | Standard Stack | 可能需要 Vite 配置调整 |

## Open Questions

1. **Vite 对 preview.html 的处理**
   - What we know: Vite 有 html 中间件可以处理根目录的 HTML 文件
   - What's unclear: preview.html 放在 frontend/ 根目录是否能通过 `localhost:5173/preview.html` 访问
   - Recommendation: 在 Plan 10-01 中首先验证这一点

2. **pixi.js v8 的 WebGPU 降级行为**
   - What we know: v8 默认尝试 WebGPU，降级到 WebGL
   - What's unclear: 降级时是否有控制台警告影响开发体验
   - Recommendation: 在 init() 中可指定 `preference: 'webgl'` 避免降级警告（如果需要）

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite 构建 + npm | ✓ | 22.22.0 | - |
| npm | 包管理 | ✓ | 10.9.4 | - |
| Vite | 开发服务器 + 构建 | ✓ | 8.0.12 | - |
| TypeScript | 类型检查 | ✓ | 6.0.2 | - |
| pixi.js | Canvas 渲染 | ✗ (未安装) | 8.18.1 (npm registry) | 无，Phase 10 核心依赖 |
| 浏览器 (Chrome/Firefox) | Canvas 运行时 | ✓ (开发环境) | - | - |

**Missing dependencies with no fallback:**
- pixi.js: planner 必须在 Plan 10-01 Wave 0 安装 (`cd frontend && npm install pixi.js`)

**Missing dependencies with fallback:**
- None

## Validation Architecture

> workflow.nyquist_validation 未在 config.json 中设置，默认启用。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | 无前端测试框架（REQUIREMENTS.md Out of Scope 明确："前端单元测试 — 第一期验证端到端链路，测试以后补"） |
| Config file | none |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RNDR-01 | PixiJS 初始化 + 3 层 Container | 手动可视化验证 | preview.html 打开浏览器 | N/A |
| RNDR-02 | 4 个固定点位显示 | 手动可视化验证 | preview.html | N/A |
| RNDR-03 | 猫咪几何图形显示 | 手动可视化验证 | preview.html | N/A |
| RNDR-04 | 3 种帧动画播放 | 手动可视化验证 | preview.html + setTimeout 测试 | N/A |
| RNDR-05 | lerp 平滑移动 | 手动可视化验证 | preview.html + setTimeout 测试 | N/A |
| RNDR-06 | 到达后切换动画 | 手动可视化验证 | preview.html + setTimeout 测试 | N/A |
| RNDR-07 | shutdown 移动到门口消失 | 手动可视化验证 | preview.html + setTimeout 测试 | N/A |

### Sampling Rate
- **Per task commit:** 手动在浏览器中刷新 preview.html 验证
- **Per wave merge:** 完整状态流程验证（idle -> thinking -> tool_call -> shutdown）
- **Phase gate:** preview.html 中 4 种状态 + 移动 + shutdown 全部正确表现

### Wave 0 Gaps
- 前端测试框架不需要（Out of Scope）
- pixi.js npm 安装需要在 Plan 10-01 开始时执行
- preview.html 需要在 Plan 10-01 中创建

## Security Domain

> 本 Phase 为纯前端 Canvas 渲染模块，不涉及网络请求、认证、数据存储或用户输入。
> 安全风险极低，跳过详细 ASVS 分析。

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | partial | VizEvent type 用 TS 字面量类型约束 |
| V6 Cryptography | no | N/A |

## Sources

### Primary (HIGH confidence)
- [PixiJS v8 Migration Guide](https://pixijs.com/8.x/guides/migrations/v8) - Application init, Graphics API, Ticker, Container 变更
- [PixiJS v8 Graphics Guide](https://pixijs.com/8.x/guides/components/scene-objects/graphics) - Graphics API 新模式、GraphicsContext
- [PixiJS v8 Graphics Fill Guide](https://pixijs.com/8.x/guides/components/scene-objects/graphics/graphics-fill) - fill() 方法详解
- [PixiJS v8 Container Guide](https://pixijs.com/8.x/guides/components/scene-objects/container) - Container 管理、子节点、排序
- [PixiJS v8 Ticker Guide](https://pixijs.com/8.x/guides/components/ticker) - Ticker 动画循环、deltaTime

### Secondary (MEDIUM confidence)
- npm registry (npm view pixi.js) - 版本号 8.18.1 确认
- Phase 9 VizEvent 实现 (framework/agent_framework/viz/viz_event.py) - 数据模型定义

### Tertiary (LOW confidence)
- WebSearch 社区讨论 - v7->v8 迁移经验（已通过官方文档交叉验证）

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PixiJS v8 是明确选型，版本已通过 npm 验证，API 通过官方文档确认
- Architecture: HIGH - 三层 Container + Ticker + lerp 是 PixiJS 标准模式
- Pitfalls: HIGH - v7->v8 API 变更全部通过官方迁移指南确认
- Code examples: HIGH - 全部基于 v8 官方文档，非 v7 模式

**Research date:** 2026-05-30
**Valid until:** 2026-06-30 (PixiJS v8 API 稳定，30 天有效)
