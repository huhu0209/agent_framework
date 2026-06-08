import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useChatStore, resetIdCounter } from './store'

// Mock fetch for SSE
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function createMockSseResponse(
  events: Array<{ type: string; payload: Record<string, unknown> }>,
  sessionId = 'test-session-1',
) {
  const sseText = events
    .map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e.payload)}\n`)
    .join('\n')

  const encoder = new TextEncoder()
  const chunk = encoder.encode(sseText)
  let readCount = 0

  return {
    ok: true,
    status: 200,
    headers: new Headers({
      'content-type': 'text/event-stream',
      'X-Session-Id': sessionId,
    }),
    body: {
      getReader: () => ({
        read: () => {
          if (readCount === 0) {
            readCount++
            return Promise.resolve({ done: false, value: chunk })
          }
          return Promise.resolve({ done: true, value: undefined })
        },
      }),
    },
    json: () => Promise.resolve({ error: 'not used' }),
  }
}

beforeEach(() => {
  resetIdCounter()
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

  it('sendMessage adds user message and streams via SSE', async () => {
    mockFetch.mockResolvedValueOnce(
      createMockSseResponse([
        { type: 'done', payload: { step: 1, content: [{ type: 'text', text: 'hi there' }] } },
        { type: 'shutdown', payload: {} },
      ]),
    )

    await useChatStore.getState().sendMessage('hello')

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/chat')
    expect(JSON.parse(options.body)).toEqual({ message: 'hello', session_id: undefined })

    const { messages } = useChatStore.getState()
    expect(messages).toHaveLength(2)
    expect(messages[0].role).toBe('user')
    expect(messages[0].content).toBe('hello')
    expect(messages[1].role).toBe('agent')
    expect(messages[1].blocks).toBeDefined()
    expect(messages[1].blocks!.length).toBe(1)
    expect(messages[1].blocks![0].kind).toBe('text_response')
    expect(useChatStore.getState().streamingMessage).toBeNull()
  })

  it('stores sessionId from response header', async () => {
    mockFetch.mockResolvedValueOnce(
      createMockSseResponse(
        [{ type: 'shutdown', payload: {} }],
        'abc123',
      ),
    )

    await useChatStore.getState().sendMessage('hello')
    expect(useChatStore.getState().sessionId).toBe('abc123')
  })

  it('reuses sessionId on subsequent calls', async () => {
    mockFetch.mockResolvedValueOnce(
      createMockSseResponse([{ type: 'shutdown', payload: {} }], 'sess-1'),
    )
    await useChatStore.getState().sendMessage('first')

    mockFetch.mockResolvedValueOnce(
      createMockSseResponse([{ type: 'shutdown', payload: {} }], 'sess-1'),
    )
    await useChatStore.getState().sendMessage('second')

    const [, options2] = mockFetch.mock.calls[1]
    expect(JSON.parse(options2.body).session_id).toBe('sess-1')
  })

  it('populates streamingMessage during streaming', async () => {
    // Create a response that delays completion
    const encoder = new TextEncoder()
    const chunk1 = encoder.encode('event: thinking\ndata: {"step":1}\n\n')
    const chunk2 = encoder.encode('event: shutdown\ndata: {}\n\n')
    let readCount = 0

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'X-Session-Id': 'stream-test' }),
      body: {
        getReader: () => ({
          read: () => {
            readCount++
            if (readCount === 1) return Promise.resolve({ done: false, value: chunk1 })
            if (readCount === 2) return new Promise((resolve) => setTimeout(() => resolve({ done: false, value: chunk2 }), 50))
            return Promise.resolve({ done: true, value: undefined })
          },
        }),
      },
    })

    const promise = useChatStore.getState().sendMessage('test')

    // Wait for streaming to start
    await new Promise((r) => setTimeout(r, 20))
    const streaming = useChatStore.getState().streamingMessage
    expect(streaming).not.toBeNull()
    expect(streaming!.role).toBe('agent')

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
      headers: new Headers(),
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

  it('handles thinking and tool_call events', async () => {
    mockFetch.mockResolvedValueOnce(
      createMockSseResponse([
        { type: 'thinking', payload: { step: 1, text: 'hmm' } },
        { type: 'tool_call', payload: { step: 1, tool_name: 'search', params: { q: 'test' } } },
        { type: 'tool_result', payload: { step: 1, content: 'found it' } },
        { type: 'done', payload: { step: 2, content: [{ type: 'text', text: 'result' }] } },
        { type: 'shutdown', payload: {} },
      ]),
    )

    await useChatStore.getState().sendMessage('search test')

    const agentMsg = useChatStore.getState().messages[1]
    expect(agentMsg.blocks).toHaveLength(4)
    expect(agentMsg.blocks![0].kind).toBe('thinking')
    expect(agentMsg.blocks![1].kind).toBe('tool_call')
    expect(agentMsg.blocks![2].kind).toBe('tool_result')
    expect(agentMsg.blocks![3].kind).toBe('text_response')
  })
})
