import { create } from 'zustand'
import type { AgentBlock, AgentBlockInit, ChatMessage, MessageRole, VizEvent } from './types'

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
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streamingMessage: null,
  agentName: 'Agent',
  isStreaming: false,
  sessionId: null,

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
