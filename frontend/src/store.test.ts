import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore, resetIdCounter } from './store'

beforeEach(() => {
  resetIdCounter()
  useChatStore.setState({
    messages: [],
    streamingMessage: null,
    connectionMode: 'mock',
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
    expect(state.connectionMode).toBe('mock')
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

  it('sendMessage adds user message and streams agent blocks', async () => {
    const store = useChatStore.getState()
    await store.sendMessage('随便说点什么')

    const { messages } = useChatStore.getState()
    expect(messages).toHaveLength(2)
    expect(messages[0].role).toBe('user')
    expect(messages[0].content).toBe('随便说点什么')
    expect(messages[1].role).toBe('agent')
    expect(messages[1].blocks).toBeDefined()
    expect(messages[1].blocks!.length).toBeGreaterThan(0)
    expect(useChatStore.getState().streamingMessage).toBeNull()
  })

  it('populates streamingMessage during streaming', async () => {
    const { sendMessage } = useChatStore.getState()

    const promise = sendMessage('随便说点什么')

    // After starting, streamingMessage should be set
    await new Promise((r) => setTimeout(r, 50))
    const streaming = useChatStore.getState().streamingMessage
    expect(streaming).not.toBeNull()
    expect(streaming!.role).toBe('agent')

    await promise

    // After completion, streamingMessage should be null
    expect(useChatStore.getState().streamingMessage).toBeNull()
  })

  it('does not send while streaming', async () => {
    useChatStore.setState({ isStreaming: true })

    const store = useChatStore.getState()
    await store.sendMessage('hello')

    expect(useChatStore.getState().messages).toHaveLength(0)
  })
})
