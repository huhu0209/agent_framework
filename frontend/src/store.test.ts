import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useChatStore, resetIdCounter } from './store'

// Mock fetch for sendViaWs
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = []
  onmessage: ((ev: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  close = vi.fn()

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  static reset() {
    MockWebSocket.instances = []
  }
}
vi.stubGlobal('WebSocket', MockWebSocket)

beforeEach(() => {
  resetIdCounter()
  MockWebSocket.reset()
  mockFetch.mockReset()
  useChatStore.setState({
    messages: [],
    streamingMessage: null,
    agentName: 'Agent',
    isStreaming: false,
    sessionId: null,
  })
})

describe('useChatStore', () => {
  it('has correct initial state', () => {
    const state = useChatStore.getState()
    expect(state.messages).toEqual([])
    expect(state.streamingMessage).toBeNull()
    expect(state.agentName).toBe('Agent')
    expect(state.isStreaming).toBe(false)
  })

  it('addSystemMessage adds a system message', () => {
    useChatStore.getState().addSystemMessage('Session started')
    const messages = useChatStore.getState().messages
    expect(messages).toHaveLength(1)
    expect(messages[0].role).toBe('system')
    expect(messages[0].content).toBe('Session started')
  })

  it('sendMessage adds user message and streams via WebSocket', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ session_id: 'test-session-1' }),
    })

    const promise = useChatStore.getState().sendMessage('hello')

    // Wait for fetch and WebSocket creation
    await new Promise((r) => setTimeout(r, 10))
    expect(mockFetch).toHaveBeenCalledTimes(1)

    // Simulate WebSocket messages
    const ws = MockWebSocket.instances[0]
    expect(ws).toBeDefined()

    ws.onmessage!({ data: JSON.stringify({
      type: 'thinking', agent: 'Agent', payload: { text: 'hmm' }, timestamp: Date.now(),
    }) })
    ws.onmessage!({ data: JSON.stringify({
      type: 'done', agent: 'Agent', payload: { text: 'hi there' }, timestamp: Date.now(),
    }) })
    ws.onmessage!({ data: JSON.stringify({
      type: 'shutdown', agent: 'Agent', payload: {}, timestamp: Date.now(),
    }) })

    await promise

    const { messages } = useChatStore.getState()
    expect(messages).toHaveLength(2)
    expect(messages[0].role).toBe('user')
    expect(messages[0].content).toBe('hello')
    expect(messages[1].role).toBe('agent')
    expect(messages[1].blocks).toBeDefined()
    expect(messages[1].blocks!.length).toBe(2)
    expect(useChatStore.getState().streamingMessage).toBeNull()
  })

  it('populates streamingMessage during streaming', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ session_id: 'test-session-2' }),
    })

    const promise = useChatStore.getState().sendMessage('test')

    await new Promise((r) => setTimeout(r, 10))
    const streaming = useChatStore.getState().streamingMessage
    expect(streaming).not.toBeNull()
    expect(streaming!.role).toBe('agent')

    // Complete the WebSocket
    const ws = MockWebSocket.instances[0]
    ws.onmessage!({ data: JSON.stringify({
      type: 'shutdown', agent: 'Agent', payload: {}, timestamp: Date.now(),
    }) })

    await promise
    expect(useChatStore.getState().streamingMessage).toBeNull()
  })

  it('does not send while streaming', async () => {
    useChatStore.setState({ isStreaming: true })

    await useChatStore.getState().sendMessage('hello')

    expect(mockFetch).not.toHaveBeenCalled()
    expect(useChatStore.getState().messages).toHaveLength(0)
  })

  it('handles fetch failure gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ error: 'Internal error' }),
    })

    await useChatStore.getState().sendMessage('hello')

    const { messages } = useChatStore.getState()
    // User message + empty agent message both present
    expect(messages).toHaveLength(2)
    expect(messages[0].role).toBe('user')
    expect(messages[1].role).toBe('agent')
    expect(messages[1].blocks).toEqual([])
    expect(useChatStore.getState().isStreaming).toBe(false)
  })
})
