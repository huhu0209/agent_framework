import { create } from 'zustand'
import type { AgentBlock, ChatMessage, MessageRole } from './types'
import { streamMockResponse } from './mock/engine'

let _nextId = 1
function uid(): string {
  return `msg-${_nextId++}-${Date.now()}`
}

export function resetIdCounter() {
  _nextId = 1
}

interface ChatStore {
  messages: ChatMessage[]
  streamingMessage: ChatMessage | null
  connectionMode: 'mock' | 'ws'
  agentName: string
  isStreaming: boolean
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streamingMessage: null,
  connectionMode: 'mock',
  agentName: 'Agent',
  isStreaming: false,

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
      for await (const block of streamMockResponse(text)) {
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
      const final = get().streamingMessage
      if (final) {
        set((s) => ({
          messages: [...s.messages, final],
          streamingMessage: null,
        }))
      }
    } finally {
      set({ isStreaming: false, streamingMessage: null })
    }
  },
}))
