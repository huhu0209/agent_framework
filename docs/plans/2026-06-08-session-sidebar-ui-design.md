# Session Sidebar UI Design

## Context

后端会话持久化已完成（transcript 模块 + sessions API），前端需要侧边栏 UI 来管理会话。

## Decision

采用方案 A：扩展现有 Zustand store，不引入新依赖。符合 ChatGPT/Claude.ai 的做法。

## Data Layer

### Store Extension (`store.ts`)

新增状态：
- `sessions: SessionInfo[]` — 会话列表
- `sidebarOpen: boolean` — 侧边栏展开/收起（默认 true）

新增类型：
```typescript
interface SessionInfo {
  session_id: string
  title: string
  created_at: number
}
```

新增 actions：
- `loadSessions()` — GET /api/v1/sessions → sessions[]
- `switchSession(id)` — GET /api/v1/chat/{id} → 替换 messages + sessionId
- `deleteSession(id)` — DELETE /api/v1/sessions/{id} → 从列表移除；如删除当前会话则触发 newSession()
- `renameSession(id, title)` — PATCH /api/v1/sessions/{id} → 更新列表对应项
- `newSession()` — 清空 messages + sessionId，生成新系统消息
- `toggleSidebar()` — sidebarOpen 取反

切换会话行为：全量替换 messages 数组和 sessionId。

## Component Layer

### New Components

**SessionSidebar.tsx**
- 固定宽度 280px，可折叠至 0px
- 顶部：新建会话按钮
- 主体：会话列表，每项显示标题和时间
- 当前活跃会话：terracotta 左边框 + ivory 背景
- 每项 hover 时显示操作图标（删除、重命名）
- 删除：inline 确认（非 modal）
- 重命名：点击后变为 inline input，回车提交

**SidebarToggle.tsx**
- 放在 ChatHeader 左侧
- hamburger/close 图标切换

### Modified Components

- **ChatLayout.tsx** — 外层从 flex-col 变为 flex-row，左侧 SessionSidebar，右侧现有布局
- **ChatHeader.tsx** — 左侧新增 SidebarToggle 按钮
- **App.tsx** — 挂载时调用 loadSessions()

## Backend Changes

### PATCH /api/v1/sessions/{session_id}

- 请求体：`{ "title": string }`
- 调用 `sm.update_title(session_id, title)`（已有方法）
- 更新 history.jsonl 记录
- 返回 `{ "status": "ok" }`

## Visual Spec (DESIGN.md compliant)

- 侧边栏背景：Parchment `#f5f4ed`
- 会话项 hover：Ivory `#faf9f5`
- 活跃会话：左边框 3px solid Terracotta `#c96442`，背景 Ivory `#faf9f5`
- 新建按钮：Warm Sand `#e8e6dc` 背景，Charcoal Warm `#4d4c48` 文字，8px radius
- 操作图标：Stone Gray `#87867f`，hover 时 Olive Gray `#5e5d59`
- 分隔线：Border Cream `#f0eee6`
- 过渡动画：transition-all duration-200 ease-in-out

## Data Flow

```
App mount → loadSessions() → GET /sessions → sessions[]

点击会话项 → switchSession(id)
  → GET /chat/{id} → HistoryResponse
  → set({ messages, sessionId })

新建会话 → newSession()
  → set({ messages: [], sessionId: null })
  → addSystemMessage("新会话已开始")
  → loadSessions()

删除会话 → deleteSession(id)
  → DELETE /sessions/{id}
  → 从 sessions[] 移除
  → 如是当前会话 → newSession()

重命名 → renameSession(id, title)
  → PATCH /sessions/{id} { title }
  → 更新 sessions[] 对应条目
```
