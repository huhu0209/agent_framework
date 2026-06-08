# Session Sidebar UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现前端侧边会话管理 UI（可折叠侧边栏 + 后端重命名端点），让用户可以新建、切换、删除、重命名会话。

**Architecture:** 扩展现有 Zustand store 新增 session 列表状态和 actions；新建 SessionSidebar 和 SidebarToggle 组件；调整 ChatLayout 为 flex-row 布局；后端新增 PATCH 端点。

**Tech Stack:** React 19, Zustand 5, Tailwind CSS v4, FastAPI, Vitest, Pytest

---

### Task 1: 后端 — PATCH /sessions/{id} 端点

**Files:**
- Modify: `backend/app/api/v1/chat.py:182` (新增路由)
- Modify: `backend/app/models/__init__.py` (新增 RenameRequest)
- Test: `backend/tests/test_chat_api.py`

**Step 1: 在 models 中新增 RenameRequest**

在 `backend/app/models/__init__.py` 末尾新增：

```python
class RenameRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        if len(v) > 100:
            raise ValueError("title too long (max 100)")
        return v
```

**Step 2: 在 chat.py 中新增 PATCH 路由**

在 `backend/app/api/v1/chat.py` 末尾追加，import 中新增 `RenameRequest`：

```python
@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameRequest, request: Request) -> dict:
    sm = request.app.state.session_manager
    sm.update_title(session_id, req.title)
    return {"status": "ok"}
```

注意：`update_title` 已在 `session.py:99` 实现，会更新 `history.jsonl`。

**Step 3: 写测试**

在 `backend/tests/test_chat_api.py` 中新增测试用例（在已有 test fixture 基础上）：

```python
async def test_rename_session(client):
    # 先创建一个会话
    resp = await client.post("/api/v1/chat", json={"message": "hello world"})
    session_id = resp.headers["X-Session-Id"]

    # 重命名
    resp = await client.patch(f"/api/v1/sessions/{session_id}", json={"title": "My Chat"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # 验证标题已更新
    resp = await client.get("/api/v1/sessions")
    sessions = resp.json()
    target = next(s for s in sessions if s["session_id"] == session_id)
    assert target["title"] == "My Chat"
```

**Step 4: 运行测试**

Run: `cd backend && pytest tests/test_chat_api.py -v -k rename`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/__init__.py backend/app/api/v1/chat.py backend/tests/test_chat_api.py
git commit -m "feat: add PATCH /sessions/{id} endpoint for renaming"
```

---

### Task 2: 前端 — 新增 SessionInfo 类型

**Files:**
- Modify: `frontend/src/types.ts`

**Step 1: 新增 SessionInfo 接口**

在 `frontend/src/types.ts` 末尾追加：

```typescript
export interface SessionInfo {
  session_id: string
  title: string
  created_at: number
}
```

**Step 2: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat: add SessionInfo type"
```

---

### Task 3: 前端 — Store 扩展（sessions 列表 + actions）

**Files:**
- Modify: `frontend/src/store.ts`
- Modify: `frontend/src/store.test.ts`

**Step 1: 写 loadSessions 的测试**

在 `store.test.ts` 的 `describe('useChatStore')` 内新增：

```typescript
it('loadSessions fetches and sets sessions', async () => {
  const sessions = [
    { session_id: 'abc123', title: 'Hello', created_at: 1700000000 },
  ]
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: () => Promise.resolve(sessions),
  })

  await useChatStore.getState().loadSessions()

  expect(mockFetch).toHaveBeenCalledWith(
    expect.stringContaining('/api/v1/sessions'),
  )
  expect(useChatStore.getState().sessions).toEqual(sessions)
})
```

**Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run store.test.ts -v -t loadSessions`
Expected: FAIL — `loadSessions` not defined

**Step 3: 在 store.ts 中扩展 ChatStore 接口**

修改 `store.ts`：

1. 在 import 行新增 `SessionInfo`
2. 在 `ChatStore` 接口新增：
```typescript
sessions: SessionInfo[]
sidebarOpen: boolean
loadSessions: () => Promise<void>
switchSession: (id: string) => Promise<void>
deleteSession: (id: string) => Promise<void>
renameSession: (id: string, title: string) => Promise<void>
newSession: () => void
toggleSidebar: () => void
```

3. 在 `useChatStore` 的初始 state 中新增：
```typescript
sessions: [],
sidebarOpen: true,
```

4. 新增 actions 实现：
```typescript
loadSessions: async () => {
  const res = await fetch(`${API_BASE}/api/v1/sessions`)
  if (res.ok) {
    const sessions = await res.json()
    set({ sessions })
  }
},

switchSession: async (id: string) => {
  const res = await fetch(`${API_BASE}/api/v1/chat/${id}`)
  if (!res.ok) return
  const data = await res.json()
  const messages: ChatMessage[] = data.messages.map((m: Record<string, unknown>, i: number) => ({
    id: `restored-${i}-${Date.now()}`,
    role: m.role as MessageRole,
    timestamp: (m.timestamp as number) ?? Date.now(),
    ...(m.content ? { content: m.content as string } : {}),
    ...(m.blocks ? { blocks: m.blocks as AgentBlock[] } : {}),
  }))
  set({ messages, sessionId: id, streamingMessage: null })
},

deleteSession: async (id: string) => {
  await fetch(`${API_BASE}/api/v1/sessions/${id}`, { method: 'DELETE' })
  const { sessions, sessionId } = get()
  const next = sessions.filter((s) => s.session_id !== id)
  set({ sessions: next })
  if (sessionId === id) {
    get().newSession()
  }
},

renameSession: async (id: string, title: string) => {
  await fetch(`${API_BASE}/api/v1/sessions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  set((s) => ({
    sessions: s.sessions.map((sess) =>
      sess.session_id === id ? { ...sess, title } : sess,
    ),
  }))
},

newSession: () => {
  set({ messages: [], sessionId: null, streamingMessage: null })
  get().addSystemMessage('新会话已开始。输入消息开始对话。')
  get().loadSessions()
},

toggleSidebar: () => {
  set((s) => ({ sidebarOpen: !s.sidebarOpen }))
},
```

**Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run store.test.ts -v`
Expected: ALL PASS

**Step 5: 更新 beforeEach 中的 reset**

在 `store.test.ts` 的 `beforeEach` 中，`useChatStore.setState` 新增：
```typescript
sessions: [],
sidebarOpen: true,
```

**Step 6: 补充更多测试**

新增以下测试：

```typescript
it('newSession clears messages and sessionId', () => {
  useChatStore.setState({
    messages: [{ id: '1', role: 'user', timestamp: 0, content: 'hi' }],
    sessionId: 'old-id',
  })

  useChatStore.getState().newSession()

  expect(useChatStore.getState().messages).toHaveLength(1) // system message
  expect(useChatStore.getState().messages[0].role).toBe('system')
  expect(useChatStore.getState().sessionId).toBeNull()
})

it('toggleSidebar flips sidebarOpen', () => {
  expect(useChatStore.getState().sidebarOpen).toBe(true)
  useChatStore.getState().toggleSidebar()
  expect(useChatStore.getState().sidebarOpen).toBe(false)
  useChatStore.getState().toggleSidebar()
  expect(useChatStore.getState().sidebarOpen).toBe(true)
})

it('switchSession loads messages from API', async () => {
  const apiMessages = [
    { role: 'user', content: 'hi', timestamp: 1700000000 },
    { role: 'agent', blocks: [{ type: 'text_response', text: 'hello' }], timestamp: 1700000001 },
  ]
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ session_id: 'abc', messages: apiMessages }),
  })

  await useChatStore.getState().switchSession('abc')

  expect(useChatStore.getState().sessionId).toBe('abc')
  const msgs = useChatStore.getState().messages
  expect(msgs).toHaveLength(2)
  expect(msgs[0].role).toBe('user')
  expect(msgs[1].role).toBe('agent')
})

it('deleteSession removes from list and resets if current', async () => {
  useChatStore.setState({
    sessions: [
      { session_id: 'a', title: 'A', created_at: 1 },
      { session_id: 'b', title: 'B', created_at: 2 },
    ],
    sessionId: 'a',
  })
  mockFetch.mockResolvedValueOnce({ ok: true })
  mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

  await useChatStore.getState().deleteSession('a')

  expect(useChatStore.getState().sessions).toHaveLength(1)
  expect(useChatStore.getState().sessionId).toBeNull()
})

it('renameSession updates title in sessions list', async () => {
  useChatStore.setState({
    sessions: [{ session_id: 'a', title: 'Old', created_at: 1 }],
  })
  mockFetch.mockResolvedValueOnce({ ok: true })

  await useChatStore.getState().renameSession('a', 'New Title')

  expect(useChatStore.getState().sessions[0].title).toBe('New Title')
})
```

**Step 7: 运行全部测试**

Run: `cd frontend && npx vitest run store.test.ts -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add frontend/src/store.ts frontend/src/store.test.ts
git commit -m "feat: extend store with session list, switch, delete, rename actions"
```

---

### Task 4: 前端 — SidebarToggle 按钮

**Files:**
- Create: `frontend/src/components/SidebarToggle.tsx`

**Step 1: 创建 SidebarToggle 组件**

创建 `frontend/src/components/SidebarToggle.tsx`：

```tsx
import { useChatStore } from '../store'

export function SidebarToggle() {
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)
  const toggleSidebar = useChatStore((s) => s.toggleSidebar)

  return (
    <button
      onClick={toggleSidebar}
      className="p-1.5 rounded-lg transition-colors"
      style={{
        color: 'var(--text-secondary)',
        backgroundColor: 'transparent',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--surface-sand)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent'
      }}
      aria-label={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        {sidebarOpen ? (
          <>
            <line x1="4" y1="4" x2="14" y2="4" />
            <line x1="4" y1="9" x2="14" y2="9" />
            <line x1="4" y1="14" x2="14" y2="14" />
            <line x1="14" y1="2" x2="14" y2="16" />
          </>
        ) : (
          <>
            <line x1="2" y1="4" x2="16" y2="4" />
            <line x1="2" y1="9" x2="16" y2="9" />
            <line x1="2" y1="14" x2="16" y2="14" />
          </>
        )}
      </svg>
    </button>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/SidebarToggle.tsx
git commit -m "feat: add SidebarToggle button component"
```

---

### Task 5: 前端 — SessionSidebar 组件

**Files:**
- Create: `frontend/src/components/SessionSidebar.tsx`

**Step 1: 创建 SessionSidebar 组件**

创建 `frontend/src/components/SessionSidebar.tsx`：

```tsx
import { useState } from 'react'
import { useChatStore } from '../store'
import type { SessionInfo } from '../types'

function SessionItem({
  session,
  isActive,
  onSelect,
  onDelete,
  onRename,
}: {
  session: SessionInfo
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onRename: (title: string) => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(session.title)
  const [confirmDelete, setConfirmDelete] = useState(false)

  if (isEditing) {
    return (
      <div className="px-2 py-1.5">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && editTitle.trim()) {
              onRename(editTitle.trim())
              setIsEditing(false)
            }
            if (e.key === 'Escape') {
              setEditTitle(session.title)
              setIsEditing(false)
            }
          }}
          onBlur={() => {
            if (editTitle.trim() && editTitle.trim() !== session.title) {
              onRename(editTitle.trim())
            }
            setIsEditing(false)
          }}
          autoFocus
          className="w-full px-2 py-1 text-sm rounded"
          style={{
            backgroundColor: 'var(--bg-ivory)',
            border: '1px solid var(--border-warm)',
            color: 'var(--text-primary)',
            outline: 'none',
          }}
        />
      </div>
    )
  }

  return (
    <div
      className="group flex items-center gap-1 px-3 py-2 cursor-pointer rounded-r-lg transition-colors"
      style={{
        backgroundColor: isActive ? 'var(--bg-ivory)' : 'transparent',
        borderLeft: isActive ? '3px solid var(--accent-terracotta)' : '3px solid transparent',
      }}
      onClick={confirmDelete ? undefined : onSelect}
      onMouseEnter={(e) => {
        if (!isActive) e.currentTarget.style.backgroundColor = 'var(--bg-ivory)'
      }}
      onMouseLeave={(e) => {
        if (!isActive) e.currentTarget.style.backgroundColor = 'transparent'
      }}
    >
      <div className="flex-1 min-w-0">
        {confirmDelete ? (
          <div className="flex items-center gap-2 text-xs">
            <span style={{ color: 'var(--text-secondary)' }}>删除？</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
                setConfirmDelete(false)
              }}
              className="px-2 py-0.5 rounded"
              style={{ backgroundColor: '#b53333', color: '#faf9f5' }}
            >
              确认
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setConfirmDelete(false)
              }}
              className="px-2 py-0.5 rounded"
              style={{ backgroundColor: 'var(--surface-sand)', color: 'var(--text-primary)' }}
            >
              取消
            </button>
          </div>
        ) : (
          <span
            className="block text-sm truncate"
            style={{
              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: isActive ? 500 : 400,
            }}
          >
            {session.title}
          </span>
        )}
      </div>
      {!confirmDelete && (
        <div
          className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => {
              setEditTitle(session.title)
              setIsEditing(true)
            }}
            className="p-1 rounded transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-secondary)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-tertiary)'
            }}
            aria-label="重命名"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" />
            </svg>
          </button>
          <button
            onClick={() => setConfirmDelete(true)}
            className="p-1 rounded transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#b53333'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-tertiary)'
            }}
            aria-label="删除"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <line x1="3" y1="4" x2="13" y2="4" />
              <line x1="5" y1="4" x2="5.5" y2="13" />
              <line x1="10.5" y1="4" x2="10" y2="13" />
              <path d="M2 4h12" />
              <path d="M5.5 1h5" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}

export function SessionSidebar() {
  const sessions = useChatStore((s) => s.sessions)
  const sessionId = useChatStore((s) => s.sessionId)
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)
  const renameSession = useChatStore((s) => s.renameSession)
  const newSession = useChatStore((s) => s.newSession)

  if (!sidebarOpen) return null

  return (
    <aside
      className="flex flex-col h-full overflow-hidden"
      style={{
        width: '280px',
        minWidth: '280px',
        backgroundColor: 'var(--bg-parchment)',
        borderRight: '1px solid var(--border-cream)',
        transition: 'width 200ms ease-in-out, min-width 200ms ease-in-out',
      }}
    >
      {/* 新建会话按钮 */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={newSession}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors"
          style={{
            backgroundColor: 'var(--surface-sand)',
            color: 'var(--text-primary)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--border-warm)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--surface-sand)'
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <line x1="7" y1="2" x2="7" y2="12" />
            <line x1="2" y1="7" x2="12" y2="7" />
          </svg>
          新建会话
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-2">
        {sessions.map((session) => (
          <SessionItem
            key={session.session_id}
            session={session}
            isActive={session.session_id === sessionId}
            onSelect={() => switchSession(session.session_id)}
            onDelete={() => deleteSession(session.session_id)}
            onRename={(title) => renameSession(session.session_id, title)}
          />
        ))}
        {sessions.length === 0 && (
          <p
            className="text-center text-xs py-8"
            style={{ color: 'var(--text-tertiary)' }}
          >
            暂无会话记录
          </p>
        )}
      </div>
    </aside>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/SessionSidebar.tsx
git commit -m "feat: add SessionSidebar component with rename/delete/new"
```

---

### Task 6: 前端 — 集成到现有布局

**Files:**
- Modify: `frontend/src/components/ChatLayout.tsx`
- Modify: `frontend/src/components/ChatHeader.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: 修改 ChatLayout 为 flex-row 布局**

修改 `frontend/src/components/ChatLayout.tsx`：

```tsx
import { ChatHeader } from './ChatHeader'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { SessionSidebar } from './SessionSidebar'

export function ChatLayout() {
  return (
    <div className="flex h-full">
      <SessionSidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <ChatHeader />
        <MessageList />
        <ChatInput />
      </div>
    </div>
  )
}
```

**Step 2: 修改 ChatHeader 新增 SidebarToggle**

修改 `frontend/src/components/ChatHeader.tsx`：

```tsx
import { useChatStore } from '../store'
import { SidebarToggle } from './SidebarToggle'

export function ChatHeader() {
  const agentName = useChatStore((s) => s.agentName)

  return (
    <header className="flex items-center gap-3 px-5 py-3"
      style={{ backgroundColor: 'var(--bg-ivory)', borderBottom: '1px solid var(--border-cream)' }}>
      <SidebarToggle />
      <span className="text-lg font-medium" style={{ fontFamily: 'var(--font-serif)' }}>
        {agentName}
      </span>
      <span className="ml-auto flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full"
        style={{
          backgroundColor: 'var(--surface-sand)',
          color: 'var(--text-tertiary)',
        }}>
        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
        Connected
      </span>
    </header>
  )
}
```

**Step 3: 修改 App.tsx 挂载时加载会话**

修改 `frontend/src/App.tsx`：

```tsx
import { useEffect, useRef } from 'react'
import { ChatLayout } from './components/ChatLayout'
import { useChatStore } from './store'

export default function App() {
  const addSystemMessage = useChatStore((s) => s.addSystemMessage)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const mounted = useRef(false)

  useEffect(() => {
    if (mounted.current) return
    mounted.current = true
    addSystemMessage('Session started. 输入消息开始对话。')
    loadSessions()
  }, [addSystemMessage, loadSessions])

  return <ChatLayout />
}
```

**Step 4: 验证前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

**Step 5: Commit**

```bash
git add frontend/src/components/ChatLayout.tsx frontend/src/components/ChatHeader.tsx frontend/src/App.tsx
git commit -m "feat: integrate sidebar into layout, load sessions on mount"
```

---

### Task 7: 手动验证

**Step 1: 启动后端**

Run: `cd backend && uvicorn main:app --port 30002 --reload`

**Step 2: 启动前端**

Run: `cd frontend && npm run dev`

**Step 3: 验证功能**

在浏览器中逐项确认：
1. 侧边栏默认展开，显示在左侧
2. 新建会话按钮工作正常
3. 发送消息后，会话出现在侧边栏列表
4. 点击侧边栏会话项可切换并加载历史消息
5. 删除会话有确认提示，删除当前会话后自动新建
6. 重命名 inline input 可用，回车或失焦提交
7. 收起/展开按钮正常工作
8. 视觉风格与 DESIGN.md 一致（parchment/terracotta/ivory 暖色调）

**Step 4: 最终 commit（如有修复）**

```bash
git add -A
git commit -m "fix: adjustments from manual verification"
```
