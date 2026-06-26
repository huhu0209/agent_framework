import { create } from 'zustand'
import { z } from 'zod'
import type { AgentBlock, AgentBlockInit, AgentDetail, AgentSummary, BucketInfo, CacheEntry, ChatMessage, ConfigPayload, InspectorState, MessageRole, SessionInfo, SkillOption, SystemPromptPayload, ToolCallEntry, UsageState, VizEvent } from './types'
import { persistCacheEntry } from './lib/cache'
import { vizWs, type WsStatus } from './lib/wsClient'

const ssePayloadSchema = z.object({
  text: z.string().optional(),
  tool_name: z.string().optional(),
  params: z.record(z.string(), z.unknown()).optional(),
  content: z.union([z.string(), z.array(z.record(z.string(), z.unknown()))]).optional(),
  error: z.string().optional(),
}).passthrough()

function toFrontendBlocks(rawBlocks: Record<string, unknown>[]): AgentBlock[] {
  return rawBlocks.map((b, i) => {
    const t = typeof b.type === 'string' ? b.type : ''
    const id = `blk-restored-${i}-${Date.now()}`
    if (t === 'text') return { id, kind: 'text_response' as const, text: typeof b.text === 'string' ? b.text : '' }
    if (t === 'tool_use') return { id, kind: 'tool_call' as const, toolName: typeof b.name === 'string' ? b.name : '', params: typeof b.input === 'object' && b.input !== null ? b.input as Record<string, unknown> : {} }
    if (t === 'tool_result') return { id, kind: 'tool_result' as const, content: typeof b.content === 'string' ? b.content : '' }
    return { id, kind: 'text_response' as const, text: '[Unrecognized block]' }
  })
}

/** 后端消息（Record）映射为前端 ChatMessage，id 由调用方提供（3 处历史拉取复用） */
function mapApiMessage(m: Record<string, unknown>, id: string): ChatMessage {
  return {
    id,
    role: m.role as MessageRole,
    timestamp: (m.timestamp as number) ?? Date.now(),
    ...(m.content ? { content: m.content as string } : {}),
    ...(m.blocks ? { blocks: toFrontendBlocks(m.blocks as Record<string, unknown>[]) } : {}),
  }
}

let _nextId = 1
function uid(): string {
  return `msg-${_nextId++}-${Date.now()}`
}

export function resetIdCounter() {
  _nextId = 1
}

export const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const API_KEY = import.meta.env.VITE_APP_API_KEY ?? ''

function applyTheme(t: 'light' | 'dark') {
  try { localStorage.setItem('chat-theme', t) } catch { /* ignore quota */ }
  document.documentElement.dataset.theme = t
}

/** A1 鉴权：所有 backend 请求需带 X-API-Key 头，值取自 VITE_APP_API_KEY */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { 'X-API-Key': API_KEY, ...extra }
}

const inflightRequests = new Map<string, Promise<{ messages: ChatMessage[], hasMore: boolean }>>()

async function fetchMessages(id: string, bucket: string): Promise<{ messages: ChatMessage[], hasMore: boolean }> {
  const existing = inflightRequests.get(id)
  if (existing) return existing

  const promise = (async () => {
    const res = await fetch(`${API_BASE}/api/v1/chat/${id}?bucket=${encodeURIComponent(bucket)}`, { headers: authHeaders() })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const messages: ChatMessage[] = data.messages.map((m: Record<string, unknown>, i: number) =>
      mapApiMessage(m, `restored-${i}-${Date.now()}`),
    )
    return { messages, hasMore: data.has_more ?? false }
  })()

  inflightRequests.set(id, promise)
  try {
    return await promise
  } finally {
    inflightRequests.delete(id)
  }
}

function vizEventToBlock(event: VizEvent): AgentBlockInit | null {
  switch (event.type) {
    case 'thinking': {
      const payload = event.payload
      const text = typeof payload.text === 'string'
        ? payload.text
        : (typeof payload.content === 'string' ? payload.content : '')
      return { kind: 'thinking', text }
    }
    case 'tool_call':
      return {
        kind: 'tool_call',
        toolName: typeof event.payload.tool_name === 'string' ? event.payload.tool_name : '',
        params: (event.payload.params as Record<string, unknown>) ?? {},
      }
    case 'tool_result':
      return {
        kind: 'tool_result',
        content: typeof event.payload.content === 'string' ? event.payload.content : '',
      }
    case 'done': {
      const content = event.payload.content
      let text = ''
      if (Array.isArray(content)) {
        const textBlock = content.find((b: Record<string, unknown>) => b.type === 'text')
        text = typeof textBlock?.text === 'string' ? textBlock.text : ''
      } else if (typeof event.payload.text === 'string') {
        text = event.payload.text
      }
      return { kind: 'text_response', text }
    }
    case 'error': {
      const msg = typeof event.payload.error === 'string'
        ? event.payload.error
        : 'Unknown error'
      return { kind: 'error', text: msg }
    }
    default:
      return null
  }
}

export type ViewName = 'chat' | 'agent' | 'teammate' | 'orchestrator'

interface ChatStore {
  messages: ChatMessage[]
  streamingMessage: ChatMessage | null
  agentName: string
  isStreaming: boolean
  sessionId: string | null
  sessions: SessionInfo[]
  currentBucket: string
  projectPath: string | null
  buckets: BucketInfo[]
  sidebarOpen: boolean
  activeView: ViewName
  sessionsLoading: boolean
  switchingSession: boolean
  messageCache: Map<string, CacheEntry>
  hasMore: boolean
  loadingOlder: boolean
  loadingFullHistory: boolean
  errorToast: string | null
  setError: (msg: string) => void
  clearError: () => void
  loadOlderMessages: () => Promise<void>
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
  loadSessions: (bucket?: string) => Promise<void>
  loadBuckets: () => Promise<void>
  setCurrentBucket: (bucket: string, projectPath: string | null) => void
  ensureBucketFor: (projectPath: string) => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  renameSession: (id: string, title: string) => Promise<void>
  newSession: () => void
  toggleSidebar: () => void
  setActiveView: (v: ViewName) => void
  prefetchSession: (id: string) => Promise<void>
  theme: 'light' | 'dark'
  searchQuery: string
  composerDraft: string
  setTheme: (t: 'light' | 'dark') => void
  toggleTheme: () => void
  setSearchQuery: (q: string) => void
  setComposerDraft: (text: string) => void
  inspectorOpen: boolean
  wsStatus: WsStatus
  inspector: InspectorState
  toggleInspector: () => void
  openInspector: () => void
  closeInspector: () => void
  connectInspector: (sid: string) => void
  disconnectInspector: () => void
  applyVizEvent: (ev: { type: string; payload: Record<string, unknown>; session_id?: string }) => void

  // --- agent 管理 ---
  agents: AgentSummary[]
  activeAgentName: string | null
  currentChatAgent: string | null
  skills: SkillOption[]
  loadAgents: () => Promise<void>
  loadSkills: () => Promise<void>
  getAgent: (name: string) => Promise<AgentDetail | null>
  createAgent: (detail: AgentDetail) => Promise<void>
  updateAgent: (name: string, detail: AgentDetail) => Promise<void>
  deleteAgent: (name: string) => Promise<void>
  setActiveAgentName: (name: string | null) => void
  setCurrentChatAgent: (name: string | null) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streamingMessage: null,
  agentName: 'Agent',
  isStreaming: false,
  sessionId: null,
  sessions: [],
  currentBucket: localStorage.getItem('af.currentBucket') ?? 'default_chat',
  projectPath: null,
  buckets: [],
  sidebarOpen: true,
  activeView: 'chat',
  sessionsLoading: false,
  switchingSession: false,
  messageCache: new Map(),
  hasMore: false,
  loadingOlder: false,
  loadingFullHistory: false,
  errorToast: null,
  theme: 'light',
  searchQuery: '',
  composerDraft: '',
  inspectorOpen: false,
  wsStatus: 'disconnected' as WsStatus,
  inspector: { config: null, systemPrompt: null, toolCalls: [], usage: null },
  agents: [],
  activeAgentName: null,
  currentChatAgent: null,
  skills: [],

  setError: (msg: string) => {
    set({ errorToast: msg })
    // 保留：错误日志供诊断（errorToast 已面向用户，此处供开发者排查）
    console.error('[ChatStore]', msg)
    setTimeout(() => set({ errorToast: null }), 5000)
  },
  clearError: () => set({ errorToast: null }),

  setTheme: (t) => { applyTheme(t); set({ theme: t }) },
  toggleTheme: () => {
    const next = get().theme === 'light' ? 'dark' : 'light'
    applyTheme(next)
    set({ theme: next })
  },
  setSearchQuery: (q: string) => set({ searchQuery: q }),
  setComposerDraft: (text: string) => set({ composerDraft: text }),
  setActiveView: (v) => set({ activeView: v }),

  toggleInspector: () => set((s) => ({ inspectorOpen: !s.inspectorOpen })),
  openInspector: () => set({ inspectorOpen: true }),
  closeInspector: () => set({ inspectorOpen: false }),

  // WS 连接生命周期跟随 sessionId（有真实 session 即连，启动即拉 config）
  connectInspector: (sid: string) => {
    if (!sid || sid.startsWith('temp-')) return
    vizWs.setHandler((ev) => get().applyVizEvent(ev))
    vizWs.setOnStatus((status) => set({ wsStatus: status }))
    vizWs.connect(sid)
  },
  disconnectInspector: () => {
    vizWs.disconnect()
    set({
      wsStatus: 'disconnected',
      inspector: { config: null, systemPrompt: null, toolCalls: [], usage: null },
    })
  },

  applyVizEvent: (ev) => {
    const p = ev.payload
    set((s) => {
      switch (ev.type) {
        case 'config':
          return { inspector: { ...s.inspector, config: p as unknown as ConfigPayload } }
        case 'system_prompt':
          return { inspector: { ...s.inspector, systemPrompt: p as unknown as SystemPromptPayload } }
        case 'tool_call': {
          const tcId = String(p.tool_call_id ?? '')
          // 去重：历史回放与实时增量并发时，同 tool_call_id 不重复追加
          if (tcId && s.inspector.toolCalls.some((t) => t.tool_call_id === tcId)) {
            return s
          }
          const tc: ToolCallEntry = {
            tool_call_id: tcId,
            tool_name: String(p.tool_name ?? ''),
            params: (p.params as Record<string, unknown>) ?? {},
            source: typeof p.source === 'string' ? p.source : undefined,
            step: typeof p.step === 'number' ? p.step : undefined,
          }
          return { inspector: { ...s.inspector, toolCalls: [...s.inspector.toolCalls, tc] } }
        }
        case 'tool_result': {
          const id = String(p.tool_call_id ?? '')
          const toolCalls = s.inspector.toolCalls.map((t) =>
            t.tool_call_id === id
              ? { ...t, content: typeof p.content === 'string' ? p.content : JSON.stringify(p.content) }
              : t,
          )
          return { inspector: { ...s.inspector, toolCalls } }
        }
        case 'usage': {
          const u = p as unknown as UsageState
          return { inspector: { ...s.inspector, usage: u } }
        }
        // 决策 1：工具链会话全量累积，不再因 idle 清空
        default:
          return s
      }
    })
  },

  addSystemMessage: (text: string) => {
    const msg: ChatMessage = {
      id: uid(),
      role: 'system' as MessageRole,
      timestamp: Date.now(),
      content: text,
    }
    set((s) => ({ messages: [...s.messages, msg] }))
  },

  sendMessage: async (text: string) => {
    if (get().isStreaming) return

    const userMsg: ChatMessage = {
      id: uid(),
      role: 'user',
      timestamp: Date.now(),
      content: text,
    }
    const agentMsg: ChatMessage = {
      id: uid(),
      role: 'agent',
      timestamp: Date.now(),
      blocks: [],
    }

    set((s) => ({
      messages: [...s.messages, userMsg],
      streamingMessage: agentMsg,
      isStreaming: true,
    }))

    try {
      await sendViaSse(text, get, set)
    } catch (e) {
      // H-FE2: 失败复用 setError toast 通道 + 注入 error block 替代空气泡
      const errMsg = e instanceof Error ? e.message : '未知错误'
      get().setError(`消息发送失败: ${errMsg}`)
      const current = get().streamingMessage
      if (current && (!current.blocks || current.blocks.length === 0)) {
        set({ streamingMessage: { ...current, blocks: [{ id: `blk-err-${Date.now()}`, kind: 'error', text: errMsg }] } })
      }
    } finally {
      const final = get().streamingMessage
      set((s) => {
        const msgs = final ? [...s.messages, final] : s.messages
        const cache = new Map(s.messageCache)
        if (s.sessionId) {
          const entry: CacheEntry = { messages: msgs, hasMore: false, cachedAt: Date.now() }
          cache.set(s.sessionId, entry)
          persistCacheEntry(s.sessionId, entry)
        }
        return {
          messages: msgs,
          streamingMessage: null,
          isStreaming: false,
          messageCache: cache,
        }
      })
    }
  },

  loadSessions: async (bucket?: string) => {
    const b = bucket ?? get().currentBucket
    set({ sessionsLoading: true })
    try {
      // preview=0：侧边栏只需 title，不触发后端 enrich（避免 redis 读/写拖慢列表）。
      // 消息按需加载：hover 预取 + 切换会话 fetchMessages。
      const res = await fetch(`${API_BASE}/api/v1/sessions?preview=0&bucket=${encodeURIComponent(b)}`, { headers: authHeaders() })
      if (res.ok) {
        const data = await res.json()
        const sessions: SessionInfo[] = Array.isArray(data) ? data : []
        // Write preview data into messageCache (don't overwrite fuller cached entries)
        const cache = new Map(get().messageCache)
        for (const session of sessions) {
          if (session.preview && session.preview.length > 0) {
            const existing = cache.get(session.session_id)
            if (existing && !existing.hasMore) {
              // Already have full data from IndexedDB — keep it
              continue
            }
            const previewMsgs = (session.preview as unknown as Record<string, unknown>[]).map((m, i) =>
              mapApiMessage(m, `preview-${i}-${Date.now()}`),
            )
            const entry: CacheEntry = {
              messages: previewMsgs,
              hasMore: (session.message_count ?? 0) > session.preview.length,
              cachedAt: Date.now(),
            }
            cache.set(session.session_id, entry)
            persistCacheEntry(session.session_id, entry)
          }
        }
        set({ sessions, sessionsLoading: false, messageCache: cache })
      } else {
        get().setError(`加载会话列表失败: HTTP ${res.status}`)
        set({ sessionsLoading: false })
      }
    } catch {
      get().setError('加载会话列表失败')
      set({ sessionsLoading: false })
    }
  },

  loadBuckets: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/buckets`, { headers: authHeaders() })
      if (res.ok) set({ buckets: await res.json() })
    } catch { /* 静默 */ }
  },

  setCurrentBucket: (bucket, projectPath) => {
    localStorage.setItem('af.currentBucket', bucket)
    set({ currentBucket: bucket, projectPath })
    void get().loadSessions(bucket)
  },

  ensureBucketFor: async (projectPath: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/bucket-for?project_path=${encodeURIComponent(projectPath)}`, { headers: authHeaders() })
      if (!res.ok) { get().setError('项目目录无效'); return }
      const { bucket } = await res.json()
      get().setCurrentBucket(bucket, projectPath)
      await get().loadBuckets()
    } catch {
      get().setError('切换项目失败')
    }
  },

  switchSession: async (id: string) => {
    const cached = get().messageCache.get(id)
    if (cached) {
      set({ messages: cached.messages, sessionId: id, streamingMessage: null, hasMore: cached.hasMore })
      get().connectInspector(id)
      // If preview data, fetch full history in background
      if (cached.hasMore) {
        set({ loadingFullHistory: true })
        const fetchStartedAt = Date.now()
        fetchMessages(id, get().currentBucket).then(({ messages, hasMore }) => {
          // H-FE3: fetch 期间若有 sendMessage 更新缓存（cachedAt > fetchStartedAt），跳过覆盖
          const current = get().messageCache.get(id)
          if (current && current.cachedAt > fetchStartedAt) {
            set({ loadingFullHistory: false })
            return
          }
          const entry: CacheEntry = { messages, hasMore, cachedAt: Date.now() }
          const cache = new Map(get().messageCache)
          cache.set(id, entry)
          persistCacheEntry(id, entry)
          // Only update if still on this session
          if (get().sessionId === id) {
            set({ messages, hasMore, messageCache: cache, loadingFullHistory: false })
          } else {
            set({ messageCache: cache, loadingFullHistory: false })
          }
        }).catch(() => {
          set({ loadingFullHistory: false })
        })
      }
      return
    }
    if (id.startsWith('temp-')) {
      // temp- 是前端占位会话，真实 id 等后端创建后由 X-Session-Id 返回。
      // 必须保持 sessionId=null，否则发消息会把 'temp-xxx' 当 session_id 发出，
      // 后端 ChatRequest.session_id 校验（^[0-9a-f]{32}$）失败 → 422。
      set({ messages: [], sessionId: null, streamingMessage: null })
      return
    }
    set({ switchingSession: true })
    try {
      const { messages, hasMore } = await fetchMessages(id, get().currentBucket)
      const entry: CacheEntry = { messages, hasMore, cachedAt: Date.now() }
      const cache = new Map(get().messageCache)
      cache.set(id, entry)
      persistCacheEntry(id, entry)
      set({ messages, sessionId: id, streamingMessage: null, switchingSession: false, messageCache: cache, hasMore })
      get().connectInspector(id)
    } catch {
      get().setError('切换会话失败')
      set({ switchingSession: false })
    }
  },

  deleteSession: async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${id}?bucket=${encodeURIComponent(get().currentBucket)}`, { method: 'DELETE', headers: authHeaders() })
      if (!res.ok) return
      const { sessions, sessionId } = get()
      const next = sessions.filter((s) => s.session_id !== id)
      const cache = new Map(get().messageCache)
      cache.delete(id)
      set({ sessions: next, messageCache: cache })
      if (sessionId === id) {
        get().newSession()
      }
    } catch {
      get().setError('删除会话失败')
    }
  },

  renameSession: async (id: string, title: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${id}?bucket=${encodeURIComponent(get().currentBucket)}`, {
        method: 'PATCH',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ title }),
      })
      if (!res.ok) return
      set((s) => ({
        sessions: s.sessions.map((sess) =>
          sess.session_id === id ? { ...sess, title } : sess,
        ),
      }))
    } catch {
      get().setError('重命名失败')
    }
  },

  newSession: () => {
    const optimistic: SessionInfo = {
      session_id: `temp-${Date.now()}`,
      title: '新对话',
      created_at: Date.now() / 1000,
    }
    set((s) => ({
      sessions: [optimistic, ...s.sessions],
      messages: [],
      sessionId: null,
      streamingMessage: null,
    }))
    get().disconnectInspector()
    get().addSystemMessage('新会话已开始。输入消息开始对话。')
  },

  toggleSidebar: () => {
    set((s) => ({ sidebarOpen: !s.sidebarOpen }))
  },

  prefetchSession: async (id: string) => {
    if (id.startsWith('temp-')) return
    const existing = get().messageCache.get(id)
    if (existing && !existing.hasMore) return
    try {
      const { messages, hasMore } = await fetchMessages(id, get().currentBucket)
      const entry: CacheEntry = { messages, hasMore, cachedAt: Date.now() }
      const cache = new Map(get().messageCache)
      cache.set(id, entry)
      set({ messageCache: cache })
      persistCacheEntry(id, entry)
    } catch {
      // prefetch failure is silent
    }
  },

  loadOlderMessages: async () => {
    const { sessionId, messages, loadingOlder } = get()
    if (!sessionId || loadingOlder || messages.length === 0) return
    const oldestTs = messages[0].timestamp / 1000
    set({ loadingOlder: true })
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/${sessionId}?limit=50&before=${oldestTs}&bucket=${encodeURIComponent(get().currentBucket)}`, { headers: authHeaders() })
      if (!res.ok) { set({ loadingOlder: false }); return }
      const data = await res.json()
      const older: ChatMessage[] = data.messages.map((m: Record<string, unknown>, i: number) =>
        mapApiMessage(m, `old-${Date.now()}-${i}`),
      )
      if (older.length === 0) { set({ loadingOlder: false, hasMore: false }); return }
      const all = [...older, ...get().messages]
      const hasMore = data.has_more ?? false
      const entry: CacheEntry = { messages: all, hasMore, cachedAt: Date.now() }
      const cache = new Map(get().messageCache)
      cache.set(sessionId, entry)
      persistCacheEntry(sessionId, entry)
      set({ messages: all, hasMore, loadingOlder: false, messageCache: cache })
    } catch {
      get().setError('加载历史消息失败')
      set({ loadingOlder: false })
    }
  },

  // --- agent 管理 ---
  loadAgents: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents`, { headers: authHeaders() })
      if (res.ok) {
        set({ agents: await res.json() })
      } else {
        get().setError(`加载 agent 列表失败: HTTP ${res.status}`)
      }
    } catch {
      get().setError('加载 agent 列表失败')
    }
  },

  loadSkills: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/skills`, { headers: authHeaders() })
      if (res.ok) {
        set({ skills: await res.json() })
      }
    } catch {
      /* 静默:skills 可选 */
    }
  },

  getAgent: async (name) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents/${encodeURIComponent(name)}`, { headers: authHeaders() })
      if (res.ok) return (await res.json()) as AgentDetail
      return null
    } catch {
      return null
    }
  },

  createAgent: async (detail) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(detail),
      })
      if (!res.ok) {
        const msg = res.status === 409 ? 'agent 已存在' : `创建失败: HTTP ${res.status}`
        get().setError(msg)
        return
      }
      await get().loadAgents()
    } catch {
      get().setError('创建 agent 失败')
    }
  },

  updateAgent: async (name, detail) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(detail),
      })
      if (!res.ok) {
        get().setError(`保存失败: HTTP ${res.status}`)
        return
      }
      await get().loadAgents()
    } catch {
      get().setError('保存 agent 失败')
    }
  },

  deleteAgent: async (name) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agents/${encodeURIComponent(name)}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (!res.ok) {
        get().setError(`删除失败: HTTP ${res.status}`)
        return
      }
      set((s) => ({
        agents: s.agents.filter((a) => a.name !== name),
        activeAgentName: s.activeAgentName === name ? null : s.activeAgentName,
      }))
    } catch {
      get().setError('删除 agent 失败')
    }
  },

  setActiveAgentName: (name) => set({ activeAgentName: name }),
  setCurrentChatAgent: (name) => set({ currentChatAgent: name }),
}))

async function sendViaSse(
  text: string,
  get: () => ChatStore,
  set: (partial: Partial<ChatStore> | ((s: ChatStore) => Partial<ChatStore>)) => void,
) {
  const currentSessionId = get().sessionId

  const res = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      message: text,
      session_id: currentSessionId ?? undefined,
      project_path: get().projectPath ?? undefined,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(err.error || `HTTP ${res.status}`)
  }

  const sessionId = res.headers.get('X-Session-Id')
  if (sessionId) {
    set((s) => {
      const tempIndex = s.sessions.findIndex(sess => sess.session_id.startsWith('temp-'))
      if (tempIndex !== -1) {
        const updated = [...s.sessions]
        updated[tempIndex] = { ...updated[tempIndex], session_id: sessionId }
        return { sessionId, sessions: updated }
      }
      return { sessionId }
    })
    if (get().sessions.some(s => s.session_id === sessionId && s.title === '新对话')) {
      get().loadSessions()
    }
    get().connectInspector(sessionId)
  }

  const body = res.body
  if (!body) {
    throw new Error('No response body received')
  }
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    let boundary: number
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      let eventType = ''
      let eventData = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) eventData = line.slice(6)
      }

      if (eventType && eventData) {
        let raw: unknown
        try {
          raw = JSON.parse(eventData)
        } catch {
          // 保留：SSE 解析失败告警供诊断
          console.warn('SSE JSON parse failed:', eventData)
          continue
        }
        const payload = ssePayloadSchema.safeParse(raw)
        if (!payload.success) {
          // 保留：SSE 校验失败告警供诊断
          console.warn('SSE payload validation failed:', payload.error.message)
          continue
        }
        handleSseEvent(eventType, payload.data, get, set)
      }
    }
  }
}

function handleSseEvent(
  type: string,
  payload: Record<string, unknown>,
  _get: () => ChatStore,
  set: (partial: Partial<ChatStore> | ((s: ChatStore) => Partial<ChatStore>)) => void,
) {
  if (type === 'idle' || type === 'shutdown') return

  const blockInit = vizEventToBlock({ type: type as VizEvent['type'], agent: 'Agent', payload, timestamp: Date.now() })
  if (!blockInit) {
    // 保留：未知事件告警，帮助发现未处理的事件类型
    console.warn('Unhandled SSE event type:', type)
    return
  }

  set((s) => {
    if (!s.streamingMessage) return s
    const block = { ...blockInit, id: `blk-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` } as AgentBlock
    return {
      streamingMessage: {
        ...s.streamingMessage,
        blocks: [...(s.streamingMessage.blocks ?? []), block],
      },
    }
  })
}
