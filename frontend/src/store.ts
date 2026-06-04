import { create } from 'zustand'
import type { AgentBlock, AgentBlockInit, ChatMessage, MessageRole, VizEvent } from './types'
import { streamMockResponse } from './mock/engine'

let _nextId = 1
function uid(): string {
  return `msg-${_nextId++}-${Date.now()}`
}

export function resetIdCounter() {
  _nextId = 1
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const WS_BASE = import.meta.env.VITE_WS_BASE ?? ''

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
    default:
      return null
  }
}

interface ChatStore {
  messages: ChatMessage[]
  streamingMessage: ChatMessage | null
  connectionMode: 'mock' | 'ws'
  agentName: string
  isStreaming: boolean
  sessionId: string | null
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
  setConnectionMode: (mode: 'mock' | 'ws') => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streamingMessage: null,
  connectionMode: 'mock',
  agentName: 'Agent',
  isStreaming: false,
  sessionId: null,

  setConnectionMode: (mode: 'mock' | 'ws') => {
    set({ connectionMode: mode })
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

    const mode = get().connectionMode

    try {
      if (mode === 'ws') {
        await sendViaWs(text, get, set)
      } else {
        await sendViaMock(get, set)
      }
    } finally {
      const final = get().streamingMessage
      set((s) => ({
        messages: final ? [...s.messages, final] : s.messages,
        streamingMessage: null,
        isStreaming: false,
      }))
    }
  },
}))

async function sendViaMock(
  _get: () => ChatStore,
  set: (partial: Partial<ChatStore> | ((s: ChatStore) => Partial<ChatStore>)) => void,
) {
  for await (const block of streamMockResponse('')) {
    set((s) => {
      if (!s.streamingMessage) return s
      return {
        streamingMessage: {
          ...s.streamingMessage,
          blocks: [...(s.streamingMessage.blocks ?? []), block as AgentBlock],
        },
      }
    })
  }
}

async function sendViaWs(
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

  const data = await res.json()
  const sessionId: string = data.session_id
  set({ sessionId })

  const wsProtocol = WS_BASE
    ? (WS_BASE.startsWith('wss') ? 'wss' : 'ws')
    : (window.location.protocol === 'https:' ? 'wss:' : 'ws:')
  const wsHost = WS_BASE
    ? WS_BASE.replace(/^wss?:\/\//, '')
    : window.location.host
  const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws/${sessionId}`

  const ws = new WebSocket(wsUrl)

  await new Promise<void>((resolve, reject) => {
    ws.onmessage = (ev) => {
      const event: VizEvent = JSON.parse(ev.data)

      if (event.type === 'idle') return

      if (event.type === 'shutdown') {
        ws.close()
        resolve()
        return
      }

      if (event.type === 'error') {
        ws.close()
        resolve()
        return
      }

      const blockInit = vizEventToBlock(event)
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

    ws.onerror = () => {
      reject(new Error('WebSocket connection failed'))
    }

    ws.onclose = () => {
      resolve()
    }
  })
}
