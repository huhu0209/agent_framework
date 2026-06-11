import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useChatStore, resetIdCounter } from './store'

vi.mock('./lib/cache', () => ({
  persistCacheEntry: vi.fn().mockResolvedValue(undefined),
}))

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
    sessions: [],
    sidebarOpen: true,
    sessionsLoading: false,
    switchingSession: false,
    messageCache: new Map(),
    hasMore: false,
    loadingOlder: false,
    loadingFullHistory: false,
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
      expect.stringContaining('/api/v1/sessions?preview=5'),
    )
    expect(useChatStore.getState().sessions).toEqual(sessions)
  })

  it('newSession clears messages and sessionId', () => {
    useChatStore.setState({
      messages: [{ id: '1', role: 'user', timestamp: 0, content: 'hi' }],
      sessionId: 'old-id',
    })
    // loadSessions mock
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

    useChatStore.getState().newSession()

    expect(useChatStore.getState().messages).toHaveLength(1)
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

    await useChatStore.getState().deleteSession('a')

    const sessions = useChatStore.getState().sessions
    // 'a' removed, newSession adds optimistic temp entry
    expect(sessions.some(s => s.session_id === 'a')).toBe(false)
    expect(sessions.some(s => s.session_id === 'b')).toBe(true)
    expect(sessions.some(s => s.session_id.startsWith('temp-'))).toBe(true)
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

  it('loadSessions sets sessionsLoading during fetch', async () => {
    let loadingDuringFetch = false
    mockFetch.mockImplementationOnce(() => {
      loadingDuringFetch = useChatStore.getState().sessionsLoading
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    })

    await useChatStore.getState().loadSessions()

    expect(loadingDuringFetch).toBe(true)
    expect(useChatStore.getState().sessionsLoading).toBe(false)
  })

  it('switchSession uses cache on second call', async () => {
    const apiMessages = [
      { role: 'user', content: 'hi', timestamp: 1700000000 },
    ]
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ session_id: 'abc', messages: apiMessages }),
    })

    await useChatStore.getState().switchSession('abc')
    expect(mockFetch).toHaveBeenCalledTimes(1)

    await useChatStore.getState().switchSession('abc')
    expect(mockFetch).toHaveBeenCalledTimes(1)
    expect(useChatStore.getState().sessionId).toBe('abc')
  })

  it('switchSession sets switchingSession during fetch', async () => {
    let switchingDuringFetch = false
    mockFetch.mockImplementationOnce(() => {
      switchingDuringFetch = useChatStore.getState().switchingSession
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ session_id: 'abc', messages: [] }),
      })
    })

    await useChatStore.getState().switchSession('abc')

    expect(switchingDuringFetch).toBe(true)
    expect(useChatStore.getState().switchingSession).toBe(false)
  })

  it('newSession adds optimistic entry to sessions', () => {
    useChatStore.setState({ sessions: [{ session_id: 'old', title: 'Old', created_at: 1 }] })
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })

    useChatStore.getState().newSession()

    const sessions = useChatStore.getState().sessions
    expect(sessions.length).toBe(2)
    expect(sessions[0].session_id).toMatch(/^temp-/)
    expect(sessions[0].title).toBe('新对话')
  })

  it('sendMessage replaces temp session ID with real one', async () => {
    useChatStore.setState({
      sessions: [{ session_id: 'temp-123', title: '新对话', created_at: 1 }],
    })
    mockFetch.mockResolvedValueOnce(
      createMockSseResponse([{ type: 'shutdown', payload: {} }], 'real-id-1'),
    )

    await useChatStore.getState().sendMessage('hello')

    const sessions = useChatStore.getState().sessions
    expect(sessions.some(s => s.session_id === 'real-id-1')).toBe(true)
    expect(sessions.some(s => s.session_id.startsWith('temp-'))).toBe(false)
  })

  it('messageCache is updated after sendMessage completes', async () => {
    mockFetch.mockResolvedValueOnce(
      createMockSseResponse([
        { type: 'done', payload: { step: 1, content: [{ type: 'text', text: 'reply' }] } },
        { type: 'shutdown', payload: {} },
      ], 'cache-test'),
    )

    await useChatStore.getState().sendMessage('hello')

    const cache = useChatStore.getState().messageCache
    expect(cache.has('cache-test')).toBe(true)
    const entry = cache.get('cache-test')!
    expect(entry.messages.length).toBe(2)
    expect(entry.hasMore).toBe(false)
  })

  it('prefetchSession populates messageCache', async () => {
    const apiMessages = [
      { role: 'user', content: 'prefetched', timestamp: 1700000000 },
    ]
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ session_id: 'prefetch-1', messages: apiMessages }),
    })

    await useChatStore.getState().prefetchSession('prefetch-1')

    const cache = useChatStore.getState().messageCache
    expect(cache.has('prefetch-1')).toBe(true)
  })

  it('prefetchSession skips if already cached', async () => {
    const cache = new Map()
    cache.set('cached-1', { messages: [{ id: '1', role: 'user' as const, timestamp: 0, content: 'hi' }], hasMore: false, cachedAt: Date.now() })
    useChatStore.setState({ messageCache: cache })

    await useChatStore.getState().prefetchSession('cached-1')

    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('deduplicates concurrent fetches for the same session', async () => {
    let fetchCount = 0
    mockFetch.mockImplementation(async () => {
      fetchCount++
      // Simulate delay so both calls overlap
      await new Promise(r => setTimeout(r, 50))
      return {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          session_id: 'aaa...aaa',
          messages: [{ role: 'user', content: 'hi', timestamp: 1000 }],
          has_more: false,
        }),
      }
    })

    // Reset cache so both miss
    useChatStore.setState({ messageCache: new Map(), messages: [], sessionId: null })

    const sid = 'a'.repeat(32)
    await Promise.all([
      useChatStore.getState().switchSession(sid),
      useChatStore.getState().prefetchSession(sid),
    ])

    expect(fetchCount).toBe(1)
    // Verify the cache is populated
    expect(useChatStore.getState().messageCache.has(sid)).toBe(true)
  })
})
