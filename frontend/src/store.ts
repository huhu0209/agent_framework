import { create } from 'zustand'
import { z } from 'zod'
import type { AgentBlock, AgentBlockInit, CacheEntry, ChatMessage, MessageRole, SessionInfo, VizEvent } from './types'
import { persistCacheEntry } from './lib/cache'

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

let _nextId = 1
function uid(): string {
  return `msg-${_nextId++}-${Date.now()}`
}

export function resetIdCounter() {
  _nextId = 1
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const inflightRequests = new Map<string, Promise<{ messages: ChatMessage[], hasMore: boolean }>>()

async function fetchMessages(id: string): Promise<{ messages: ChatMessage[], hasMore: boolean }> {
  const existing = inflightRequests.get(id)
  if (existing) return existing

  const promise = (async () => {
    const res = await fetch(`${API_BASE}/api/v1/chat/${id}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const messages: ChatMessage[] = data.messages.map((m: Record<string, unknown>, i: number) => ({
      id: `restored-${i}-${Date.now()}`,
      role: m.role as MessageRole,
      timestamp: (m.timestamp as number) ?? Date.now(),
      ...(m.content ? { content: m.content as string } : {}),
      ...(m.blocks ? { blocks: toFrontendBlocks(m.blocks as Record<string, unknown>[]) } : {}),
    }))
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

interface ChatStore {
  messages: ChatMessage[]
  streamingMessage: ChatMessage | null
  agentName: string
  isStreaming: boolean
  sessionId: string | null
  sessions: SessionInfo[]
  sidebarOpen: boolean
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
  loadSessions: () => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  renameSession: (id: string, title: string) => Promise<void>
  newSession: () => void
  toggleSidebar: () => void
  prefetchSession: (id: string) => Promise<void>
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streamingMessage: null,
  agentName: 'Agent',
  isStreaming: false,
  sessionId: null,
  sessions: [],
  sidebarOpen: true,
  sessionsLoading: false,
  switchingSession: false,
  messageCache: new Map(),
  hasMore: false,
  loadingOlder: false,
  loadingFullHistory: false,
  errorToast: null,

  setError: (msg: string) => {
    set({ errorToast: msg })
    console.error('[ChatStore]', msg)
    setTimeout(() => set({ errorToast: null }), 5000)
  },
  clearError: () => set({ errorToast: null }),

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
    } catch {
      // Error handled: streamingMessage finalized in finally
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

  loadSessions: async () => {
    set({ sessionsLoading: true })
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions?preview=5`)
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
            const previewMsgs = (session.preview as unknown as Record<string, unknown>[]).map((m, i) => ({
              id: `preview-${i}-${Date.now()}`,
              role: m.role as MessageRole,
              timestamp: (m.timestamp as number) ?? Date.now(),
              ...(m.content ? { content: m.content as string } : {}),
              ...(m.blocks ? { blocks: toFrontendBlocks(m.blocks as Record<string, unknown>[]) } : {}),
            }))
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

  switchSession: async (id: string) => {
    const cached = get().messageCache.get(id)
    if (cached) {
      set({ messages: cached.messages, sessionId: id, streamingMessage: null, hasMore: cached.hasMore })
      // If preview data, fetch full history in background
      if (cached.hasMore) {
        set({ loadingFullHistory: true })
        fetchMessages(id).then(({ messages, hasMore }) => {
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
      set({ messages: [], sessionId: id, streamingMessage: null })
      return
    }
    set({ switchingSession: true })
    try {
      const { messages, hasMore } = await fetchMessages(id)
      const entry: CacheEntry = { messages, hasMore, cachedAt: Date.now() }
      const cache = new Map(get().messageCache)
      cache.set(id, entry)
      persistCacheEntry(id, entry)
      set({ messages, sessionId: id, streamingMessage: null, switchingSession: false, messageCache: cache, hasMore })
    } catch {
      get().setError('切换会话失败')
      set({ switchingSession: false })
    }
  },

  deleteSession: async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${id}`, { method: 'DELETE' })
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
      const res = await fetch(`${API_BASE}/api/v1/sessions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
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
      const { messages, hasMore } = await fetchMessages(id)
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
      const res = await fetch(`${API_BASE}/api/v1/chat/${sessionId}?limit=50&before=${oldestTs}`)
      if (!res.ok) { set({ loadingOlder: false }); return }
      const data = await res.json()
      const older: ChatMessage[] = data.messages.map((m: Record<string, unknown>, i: number) => ({
        id: `old-${Date.now()}-${i}`,
        role: m.role as MessageRole,
        timestamp: (m.timestamp as number) ?? Date.now(),
        ...(m.content ? { content: m.content as string } : {}),
        ...(m.blocks ? { blocks: toFrontendBlocks(m.blocks as Record<string, unknown>[]) } : {}),
      }))
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
}))

async function sendViaSse(
  text: string,
  get: () => ChatStore,
  set: (partial: Partial<ChatStore> | ((s: ChatStore) => Partial<ChatStore>)) => void,
) {
  const currentSessionId = get().sessionId

  const res = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: text,
      session_id: currentSessionId ?? undefined,
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
          console.warn('SSE JSON parse failed:', eventData)
          continue
        }
        const payload = ssePayloadSchema.safeParse(raw)
        if (!payload.success) {
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
