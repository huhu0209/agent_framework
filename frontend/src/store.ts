import { create } from 'zustand'
import type { AgentBlock, ChatMessage, MessageRole } from './types'
import { streamMockResponse } from './mock/engine'

let nextId = 1
function uid(): string {
  return `msg-${nextId++}-${Date.now()}`
}

interface ChatStore {
  messages: ChatMessage[]
  connectionMode: 'mock' | 'ws'
  agentName: string
  isStreaming: boolean
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
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
      messages: [...s.messages, userMsg, agentMsg],
      isStreaming: true,
    }))

    try {
      for await (const block of streamMockResponse(text)) {
        set((s) => {
          const msgs = [...s.messages]
          const lastIdx = msgs.length - 1
          const last = msgs[lastIdx]
          if (last.role !== 'agent') return s
          msgs[lastIdx] = {
            ...last,
            blocks: [...(last.blocks ?? []), block as AgentBlock],
          }
          return { messages: msgs }
        })
      }
    } finally {
      set({ isStreaming: false })
    }
  },
}))
