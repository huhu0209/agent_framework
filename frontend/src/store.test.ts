import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useChatStore, resetIdCounter, resetInflightAgents } from './store'

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
  resetInflightAgents()
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
    // toEqual 把 {a: undefined} 和缺失 key 视作相等；但新增 project_path/agent_name 字段后会脆裂，
    // 故只断言 message 字段（其余字段由专门测试覆盖）。
    expect(JSON.parse(options.body)).toEqual(expect.objectContaining({ message: 'hello' }))

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

  it('handles fetch failure with error feedback', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: () => Promise.resolve({ error: 'Internal error' }),
    })

    await useChatStore.getState().sendMessage('hello')

    const { messages } = useChatStore.getState()
    expect(messages).toHaveLength(2)
    expect(messages[0].role).toBe('user')
    expect(messages[1].role).toBe('agent')
    // H-FE2: 失败注入 error block（替代空气泡）
    expect(messages[1].blocks?.[0]?.kind).toBe('error')
    expect(useChatStore.getState().isStreaming).toBe(false)
    // H-FE2: setError 触发 toast
    expect(useChatStore.getState().errorToast).not.toBeNull()
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
      expect.stringContaining('/api/v1/sessions?preview=0'),
      expect.objectContaining({ headers: expect.any(Object) }),
    )
    expect(useChatStore.getState().sessions).toEqual(sessions)
  })

  it('loadBuckets keeps current bucket in list when backend omits it', async () => {
    useChatStore.setState({ currentBucket: 'myproject_abcd1234' })
    // 后端扫不到未建目录的桶,只返回 default_chat
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([{ bucket: 'default_chat', display_name: 'default_chat' }]),
    })
    await useChatStore.getState().loadBuckets()

    const names = useChatStore.getState().buckets.map((b) => b.bucket)
    expect(names).toContain('myproject_abcd1234')
    expect(names).toContain('default_chat')
    const cur = useChatStore.getState().buckets.find((b) => b.bucket === 'myproject_abcd1234')
    expect(cur?.display_name).toBe('myproject')
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

  it('switchSession background fetch does not overwrite newer cache', async () => {
    // 预置 preview 缓存（hasMore=true，触发后台 full fetch）
    useChatStore.setState({
      messageCache: new Map([['s1', {
        messages: [{ id: 'p1', role: 'user' as const, timestamp: 1, content: 'preview' }],
        hasMore: true,
        cachedAt: 100,
      }]]),
    })

    // 后台 full fetch 返回旧历史，延迟 resolve（让测试在 resolve 前更新 cache）
    let resolveFetch!: () => void
    const pending = new Promise<void>((r) => { resolveFetch = r })
    mockFetch.mockReturnValueOnce(pending.then(() => ({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        session_id: 's1',
        messages: [{ role: 'user', content: 'old full', timestamp: 1 }],
        has_more: false,
      }),
    })))

    await useChatStore.getState().switchSession('s1')
    // 命中缓存立即返回；后台 fetch pending（fetchStartedAt = T1）

    // 模拟：fetch resolve 前，用户发了新消息（sendMessage finally 更新 cache cachedAt = T2 > T1）
    useChatStore.setState({
      messageCache: new Map([['s1', {
        messages: [{ id: 'new', role: 'user' as const, timestamp: 999, content: 'new msg' }],
        hasMore: false,
        cachedAt: Date.now() + 10000, // 确保大于 fetchStartedAt
      }]]),
      messages: [{ id: 'new', role: 'user' as const, timestamp: 999, content: 'new msg' }],
      sessionId: 's1',
    })

    resolveFetch()
    await new Promise((r) => setTimeout(r, 30)) // 等 .then 写回执行

    // H-FE3: 新消息不被过期 full 覆盖
    expect(useChatStore.getState().messages[0]?.content).toBe('new msg')
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

  it('applyVizEvent 处理 usage 事件更新 inspector.usage', () => {
    useChatStore.setState({
      inspector: { config: null, systemPrompt: null, toolCalls: [], usage: null },
    })
    useChatStore.getState().applyVizEvent({
      type: 'usage', session_id: 's1',
      payload: { input: 1000, output: 200, cumulative_input: 3000, cumulative_output: 600, max_context: 200000 },
    })
    expect(useChatStore.getState().inspector.usage).toEqual({
      input: 1000, output: 200, cumulative_input: 3000, cumulative_output: 600, max_context: 200000,
    })
  })

  it('applyVizEvent 多次 usage 覆盖为最新值', () => {
    useChatStore.setState({
      inspector: { config: null, systemPrompt: null, toolCalls: [], usage: null },
    })
    const store = useChatStore.getState()
    store.applyVizEvent({
      type: 'usage', session_id: 's1',
      payload: { input: 1000, output: 200, cumulative_input: 1000, cumulative_output: 200, max_context: 200000 },
    })
    store.applyVizEvent({
      type: 'usage', session_id: 's1',
      payload: { input: 1500, output: 300, cumulative_input: 2500, cumulative_output: 500, max_context: 200000 },
    })
    expect(useChatStore.getState().inspector.usage).toEqual({
      input: 1500, output: 300, cumulative_input: 2500, cumulative_output: 500, max_context: 200000,
    })
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

describe('theme / searchQuery / composerDraft', () => {
  beforeEach(() => {
    localStorage.clear()
    useChatStore.setState({ theme: 'light', searchQuery: '', composerDraft: '' })
  })

  it('toggleTheme 翻转 light↔dark 并持久化 + 同步 document', () => {
    useChatStore.setState({ theme: 'light' })
    useChatStore.getState().toggleTheme()
    expect(useChatStore.getState().theme).toBe('dark')
    expect(localStorage.getItem('chat-theme')).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('setSearchQuery 更新搜索词', () => {
    useChatStore.getState().setSearchQuery('adapter')
    expect(useChatStore.getState().searchQuery).toBe('adapter')
  })

  it('setComposerDraft 更新草稿', () => {
    useChatStore.getState().setComposerDraft('你好')
    expect(useChatStore.getState().composerDraft).toBe('你好')
  })
})

describe('store bucket state', () => {
  beforeEach(() => localStorage.clear())

  it('loadSessions sends bucket query', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] })

    await useChatStore.getState().loadSessions('projA_abcd1234')

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('bucket=projA_abcd1234')
  })

  it('setCurrentBucket persists to localStorage and updates state', () => {
    useChatStore.getState().setCurrentBucket('projB_ffff', '/tmp/projB')

    expect(useChatStore.getState().currentBucket).toBe('projB_ffff')
    expect(useChatStore.getState().projectPath).toBe('/tmp/projB')
    expect(localStorage.getItem('af.currentBucket')).toBe('projB_ffff')
  })

  // 修复跨桶 404：fetchMessages 透传 currentBucket（经由 switchSession 触发）
  it('switchSession fetchMessages sends currentBucket query', async () => {
    useChatStore.setState({ currentBucket: 'projA_abcd1234', messageCache: new Map() })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ session_id: 's1', messages: [] }),
    })

    await useChatStore.getState().switchSession('s1')

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('/api/v1/chat/s1')
    expect(url).toContain('bucket=projA_abcd1234')
  })

  it('deleteSession sends currentBucket query', async () => {
    useChatStore.setState({
      currentBucket: 'projA_abcd1234',
      sessions: [{ session_id: 'a', title: 'A', created_at: 1 }],
      sessionId: null,
    })
    mockFetch.mockResolvedValueOnce({ ok: true })

    await useChatStore.getState().deleteSession('a')

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('/api/v1/sessions/a')
    expect(url).toContain('bucket=projA_abcd1234')
  })

  it('renameSession sends currentBucket query', async () => {
    useChatStore.setState({
      currentBucket: 'projA_abcd1234',
      sessions: [{ session_id: 'a', title: 'Old', created_at: 1 }],
    })
    mockFetch.mockResolvedValueOnce({ ok: true })

    await useChatStore.getState().renameSession('a', 'New')

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('/api/v1/sessions/a')
    expect(url).toContain('bucket=projA_abcd1234')
  })

  // loadOlderMessages：bucket 透传 + 补 authHeaders（修复历史 401）
  it('loadOlderMessages sends currentBucket query and authHeaders', async () => {
    useChatStore.setState({
      currentBucket: 'projA_abcd1234',
      sessionId: 's1',
      messages: [{ id: 'm1', role: 'user', timestamp: 1700000000000, content: 'hi' }],
    })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ messages: [], has_more: false }),
    })

    await useChatStore.getState().loadOlderMessages()

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/chat/s1')
    expect(url).toContain('bucket=projA_abcd1234')
    expect((options.headers as Record<string, string>)['X-API-Key']).toBeDefined()
  })
})

describe('agent management', () => {
  beforeEach(() => {
    useChatStore.setState({ agents: [], activeAgentName: null, skills: [] })
  })

  it('loadAgents 拉取并写入 agents', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200,
      json: () => Promise.resolve([{ name: 'reviewer', description: '审查员' }]),
    })
    await useChatStore.getState().loadAgents()
    expect(useChatStore.getState().agents).toEqual([{ name: 'reviewer', description: '审查员' }])
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/agents'),
      expect.objectContaining({ headers: expect.any(Object) }),
    )
  })

  it('createAgent POST 后刷新列表', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 201, json: () => Promise.resolve({ name: 'a' }) })
    mockFetch.mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([]) })
    await useChatStore.getState().createAgent({
      name: 'a', description: '', model: null, skills: null, tools: null,
      permission_mode: 'ask', soul: '', identity: '', agents_rules: '', tool_guidance: '',
    })
    expect(mockFetch).toHaveBeenNthCalledWith(1,
      expect.stringContaining('/api/v1/agents'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('loadSkills 写入 skills', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200,
      json: () => Promise.resolve([{ name: 'web-search', description: '联网搜索' }]),
    })
    await useChatStore.getState().loadSkills()
    expect(useChatStore.getState().skills).toEqual([{ name: 'web-search', description: '联网搜索' }])
  })

  it('deleteAgent 删除后调 loadAgents 刷新(LOW#7)', async () => {
    useChatStore.setState({ agents: [{ name: 'a', description: '' }], activeAgentName: 'a' })
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204, json: () => Promise.resolve(null) })
    mockFetch.mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([]) })
    await useChatStore.getState().deleteAgent('a')
    expect(mockFetch).toHaveBeenNthCalledWith(1,
      expect.stringContaining('/api/v1/agents/a'),
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(mockFetch).toHaveBeenCalledTimes(2)  // DELETE + loadAgents 刷新(非本地乐观 filter)
    expect(useChatStore.getState().activeAgentName).toBeNull()
  })

  it('deleteAgent 失败返回 false 且不清 activeAgentName(HIGH-1)', async () => {
    useChatStore.setState({ agents: [{ name: 'a', description: '' }], activeAgentName: 'a' })
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 })
    const ok = await useChatStore.getState().deleteAgent('a')
    expect(ok).toBe(false)
    expect(useChatStore.getState().activeAgentName).toBe('a')  // 失败不清空
    expect(mockFetch).toHaveBeenCalledTimes(1)  // 失败不触发 loadAgents 刷新
  })

  it('loadAgents 并发调用去重(LOW#8)', async () => {
    type FetchResp = { ok: boolean; status: number; json: () => Promise<unknown> }
    let resolveFetch!: (v: FetchResp) => void
    mockFetch.mockImplementationOnce(() => new Promise<FetchResp>((res) => { resolveFetch = res }))
    // 并发两次 loadAgents — 第二次应复用 inflight,不二次 fetch
    const p1 = useChatStore.getState().loadAgents()
    const p2 = useChatStore.getState().loadAgents()
    resolveFetch({ ok: true, status: 200, json: () => Promise.resolve([]) })
    await Promise.all([p1, p2])
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })
})

describe('chat agent 绑定', () => {
  beforeEach(() => {
    useChatStore.setState({
      agents: [{ name: 'reviewer', description: '' }],
      currentChatAgent: null,
      sessionId: null,
      isStreaming: false,
    })
  })

  it('setCurrentChatAgent 切换当前 agent', () => {
    useChatStore.getState().setCurrentChatAgent('reviewer')
    expect(useChatStore.getState().currentChatAgent).toBe('reviewer')
  })

  it('sendMessage 请求体带 currentChatAgent 作为 agent_name', async () => {
    useChatStore.setState({ currentChatAgent: 'reviewer' })
    mockFetch.mockResolvedValueOnce(createMockSseResponse([]))
    await useChatStore.getState().sendMessage('hi')
    const call = mockFetch.mock.calls[0]
    const body = JSON.parse(call[1].body)
    expect(body.agent_name).toBe('reviewer')
  })

  it('currentChatAgent 为 null 时 agent_name 为 undefined', async () => {
    mockFetch.mockResolvedValueOnce(createMockSseResponse([]))
    await useChatStore.getState().sendMessage('hi')
    const call = mockFetch.mock.calls[0]
    const body = JSON.parse(call[1].body)
    expect(body.agent_name).toBeUndefined()
  })
})
