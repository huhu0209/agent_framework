# Phase 19: Frontend 全面修复 - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

修复 v0.0.4 审查中发现的 11 个前端问题（FT-SEC-01~02, FT-LOGIC-01~04, FT-ARCH-01~05）：SSE payload 验证、react-markdown HTML 消毒、res.body null check、JSON.parse 错误处理、虚拟列表 auto-scroll、hoverRef timeout 清理、toFrontendBlocks 类型安全、store 错误反馈、SSE unknown stop reason 处理、orphan tool_result、inline hover 样式替换。

修复范围仅限 `frontend/src/`，不涉及 backend/ 或 framework/。

</domain>

<decisions>
## Implementation Decisions

### SSE 验证方案（FT-SEC-01, FT-LOGIC-01, FT-LOGIC-02）
- **D-01:** 轻量 zod 验证 — 仅验证 payload 是 object + 关键字段（text、tool_name、content、error）是 string。约 20 行代码，不定义完整 per-event schema
- **D-02:** 验证位置在 JSON.parse 后、handleSseEvent 前 — 拦截最早，malformed 数据不进入渲染链
- **D-03:** 验证失败跳过该事件 + console.warn — 用户体验不受影响，仅丢失单个畸形事件
- **D-04:** 添加 zod 依赖到 frontend — 项目已是全 TS 栈，zod 是 TS 生态标准验证库

### Store 错误反馈机制（FT-ARCH-02）
- **D-05:** Toast 通知方式反馈错误 — 添加 errorToast: string | null 到 ChatStore 接口
- **D-06:** Store 状态管理 — errorToast + clearError() action，组件渲染 Toast 组件。同时添加 console.error 记录
- **D-07:** 所有网络错误场景覆盖 — fetch 失败（deleteSession、renameSession、loadSessions、switchSession）、SSE 解析失败、非 ok 响应
- **D-08:** 5 秒自动消失 — setError 时 setTimeout(5000) 调用 clearError

### Auto-scroll 行为（FT-LOGIC-03）
- **D-09:** 智能 auto-scroll — 底部附近（100px 阈值）自动滚动，用户上滚后禁用
- **D-10:** 用 virtualizer API（scrollToIndex）判断和执行滚动
- **D-11:** 初始加载和会话切换也自动滚动到底部

### hoverRef 清理 + hover 样式（FT-LOGIC-04, FT-ARCH-05）
- **D-12:** SessionItem 添加 useEffect cleanup 清除 hoverRef.current timeout
- **D-13:** SessionSidebar + SidebarToggle 的 onMouseEnter/onMouseLeave 替换为 Tailwind hover: utility classes

### toFrontendBlocks 类型安全 + groupBlocks（FT-ARCH-01, FT-ARCH-04）
- **D-14:** toFrontendBlocks 添加运行时类型检查 — 用 zod 或 typeof 验证 b.type 是 string，b.text/b.name/b.content 是 string，fallback 时 JSON.stringify(b) 改为显示 "Unrecognized block" 而非暴露内部数据
- **D-15:** groupBlocks 处理 orphan tool_result — 向前搜索匹配的 tool_call，未找到则作为独立 tool_result block 渲染

### SSE unknown stop reason（FT-ARCH-03）
- **D-16:** handleSseEvent 对未知事件类型（default case）console.warn 记录事件类型，而非完全静默丢弃

### rehype-sanitize（FT-SEC-02）
- **D-17:** 添加 rehype-sanitize 到 react-markdown 配置 — 使用默认 schema 作为纵深防御。添加注释：严禁添加 rehype-raw 除非同时配置 rehype-sanitize

### Plan 分组策略
- **D-18:** 按文件分 2 plan：
  - Plan A: store.ts 集中修复 — SSE 验证 + null check + JSON.parse + errorToast + toFrontendBlocks + groupBlocks + handleSseEvent 清理（7 个 issue，store.ts 是最密集文件）
  - Plan B: 组件修复 — auto-scroll + hoverRef cleanup + hover→Tailwind + rehype-sanitize（4 个 issue）
- **D-19:** Plan A（store.ts）先行 — 核心数据层先修好，组件修复可以引用新的 errorToast 状态

### 验证策略
- **D-20:** `npm run build` 验证 — 每个 plan 完成后确认无 TypeScript 错误
- **D-21:** `vitest run` 验证 — 确认现有测试仍通过
- **D-22:** 手动验证 SSE 流式响应、错误反馈、auto-scroll 行为

### Claude's Discretion
- zod 验证 schema 的具体字段定义和命名
- errorToast 组件的具体实现和样式
- virtualizer auto-scroll 的具体 API 使用方式
- toFrontendBlocks 运行时检查的具体实现
- groupBlocks orphan 处理的具体逻辑
- 每个 plan 内部的修复顺序

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审查报告（问题来源）
- `docs/reviews/REVIEW-FRONTEND.md` — 全部 FRNT-* issue 详情（含文件位置、影响分析、修复建议）
  - FRNT-SEC-01 (SSE event data 无 schema 验证, HIGH)
  - FRNT-SEC-02 (react-markdown 无 rehype-sanitize, HIGH)
  - FRNT-LOGIC-01 (res.body! 非空断言, HIGH)
  - FRNT-LOGIC-02 (JSON.parse 无错误处理, HIGH)
  - FRNT-LOGIC-06 (hoverRef timeout 未清理, HIGH) → FT-LOGIC-04
  - FRNT-LOGIC-07 (Virtual list 不自动滚动, HIGH) → FT-LOGIC-03
  - FRNT-ARCH-02 (toFrontendBlocks 不安全类型断言, MEDIUM) → FT-ARCH-01
  - FRNT-LOGIC-03 (deleteSession 无 try-catch, MEDIUM) → FT-ARCH-02
  - FRNT-LOGIC-04 (loadSessions 吞错误, MEDIUM) → FT-ARCH-02
  - FRNT-LOGIC-05 (switchSession 吞错误, MEDIUM) → FT-ARCH-02
  - FRNT-ARCH-03 (sendViaSse standalone, MEDIUM) → FT-ARCH-03
  - FRNT-LOGIC-09 (groupBlocks orphan tool_result, MEDIUM) → FT-ARCH-04
  - FRNT-ARCH-11 (inline hover styles, MEDIUM) → FT-ARCH-05
  - FRNT-ARCH-15 (SidebarToggle hover, MEDIUM) → FT-ARCH-05

### 需求定义
- `.planning/REQUIREMENTS.md` — FT-SEC-01~02, FT-LOGIC-01~04, FT-ARCH-01~05 需求定义
- `.planning/ROADMAP.md` — Phase 19 目标、成功标准、范围定义

### 前端源码（修改目标）
- `frontend/src/store.ts` (389 行) — SSE 解析、vizEventToBlock、sendViaSse、handleSseEvent、fetchMessages、loadSessions、switchSession、deleteSession、renameSession、toFrontendBlocks
- `frontend/src/components/MessageList.tsx` (95 行) — auto-scroll 逻辑
- `frontend/src/components/SessionSidebar.tsx` (256 行) — hoverRef cleanup + hover→Tailwind
- `frontend/src/components/SidebarToggle.tsx` (41 行) — hover→Tailwind
- `frontend/src/components/TextResponseBlock.tsx` (43 行) — rehype-sanitize
- `frontend/src/components/AgentResponse.tsx` (67 行) — groupBlocks orphan 处理
- `frontend/src/types.ts` (40 行) — 类型定义参考
- `frontend/package.json` — 添加 zod + rehype-sanitize 依赖

### 前序阶段上下文
- `.planning/phases/18-backend/18-CONTEXT.md` — Backend SSE 错误分类（ErrorCategory 枚举 + 用户友好消息），CORS 收紧，session_id 验证

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `vizEventToBlock` 已有部分 typeof 检查 — `typeof payload.text === 'string'`、`typeof event.payload.tool_name === 'string'` 等。可扩展为 zod 验证的基础
- `handleSseEvent` 已过滤 idle/shutdown 事件 — 扩展 default case 添加 console.warn 即可
- `@tanstack/react-virtual` 已提供 `scrollToIndex` API — auto-scroll 可直接使用
- `useChatStore` Zustand store — 添加 errorToast 字段符合现有模式
- Tailwind CSS 4 已配置 — hover: utilities 可直接使用

### Established Patterns
- Zustand store 管理 — 所有状态通过 create<ChatStore> 集中管理，新字段遵循相同模式
- React 19 + TypeScript — 严格类型检查，`npm run build` 会捕获类型错误
- SSE 事件处理链 — JSON.parse → handleSseEvent → vizEventToBlock → set(streamingMessage)
- 组件结构 — 函数组件 + hooks，无 class 组件

### Integration Points
- zod 需添加到 frontend/package.json dependencies
- rehype-sanitize 需添加到 frontend/package.json dependencies
- errorToast 需要新的 Toast 组件（可在 App.tsx 或 ChatLayout.tsx 中渲染）
- auto-scroll 需修改 MessageList.tsx 的 virtualizer 配置
- hover→Tailwind 需替换 SessionSidebar.tsx 和 SidebarToggle.tsx 中的 onMouseEnter/onMouseLeave

</code_context>

<specifics>
## Specific Ideas

- zod 验证 schema 示例：`z.object({ text: z.string().optional(), tool_name: z.string().optional(), content: z.string().optional(), error: z.string().optional() }).passthrough()`
- errorToast 组件建议放在 ChatLayout.tsx 中，fixed 定位在右上角
- auto-scroll 用 `virtualizer.scrollToIndex(allItems.length - 1, { align: 'end' })` 实现
- hover→Tailwind 替换：`onMouseEnter={e => e.currentTarget.style.backgroundColor = '...'}` → `hover:bg-[var(--surface-sand)]` class
- toFrontendBlocks fallback 从 `JSON.stringify(b)` 改为显示 "Unrecognized block type" 或类似用户友好消息
- Phase 18 已将 SSE error 改为分类消息，前端 error block 渲染将直接展示分类后的友好消息

</specifics>

<deferred>
## Deferred Ideas

- FRNT-ARCH-10 (SessionItem 组件职责过多) — 需组件拆分重构，留后续 milestone
- FRNT-ARCH-12 (estimateSize: () => 80 静态估计) — 需 measureElement 集成，留后续优化
- FRNT-ARCH-13 (ToolCallBlock result prop 类型过松) — 类型收窄，可在后续补写前端测试时一并处理
- FRNT-ARCH-16 (Connected 状态硬编码) — 需后端 health endpoint，留后续
- FRNT-LOGIC-10 (clipboard.writeText 非 HTTPS 失败) — MEDIUM 级别，留后续
- FRNT-LOGIC-08 (adjustHeight 初始渲染) — 当前无可见问题，留后续
- 前端单元测试补写 — 需专门 milestone

</deferred>

---

*Phase: 19-Frontend 全面修复*
*Context gathered: 2026-06-10*
