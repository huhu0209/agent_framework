import { create } from 'zustand'
import type { AgentBlock, AgentBlockInit, ChatMessage, MessageRole, SessionInfo, VizEvent } from './types'

let _nextId = 1
function uid(): string {
  return `msg-${_nextId++}-${Date.now()}`
}

export function resetIdCounter() {
  _nextId = 1
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

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
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
  loadSessions: () => Promise<void>
  switchSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  renameSession: (id: string, title: string) => Promise<void>
  newSession: () => void
  toggleSidebar: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streamingMessage: null,
  agentName: 'Agent',
  isStreaming: false,
  sessionId: null,
  sessions: [],
  sidebarOpen: true,

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
      set((s) => ({
        messages: final ? [...s.messages, final] : s.messages,
        streamingMessage: null,
        isStreaming: false,
      }))
    }
  },

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
  if (sessionId) set({ sessionId })

  const reader = res.body!.getReader()
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
        const payload = JSON.parse(eventData)
        handleSseEvent(eventType, payload, get, set)
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
  if (!blockInit) return

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
