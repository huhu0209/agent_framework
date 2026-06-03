import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore } from './store'

beforeEach(() => {
  useChatStore.setState({
    messages: [],
    connectionMode: 'mock',
    agentName: 'Agent',
    isStreaming: false,
  })
})

describe('useChatStore', () => {
  it('has correct initial state', () => {
    const state = useChatStore.getState()
    expect(state.messages).toEqual([])
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

  it('sendMessage adds user message and agent message with blocks', async () => {
    const store = useChatStore.getState()
    await store.sendMessage('随便说点什么')

    const messages = useChatStore.getState().messages
    expect(messages.length).toBeGreaterThanOrEqual(2)
    expect(messages[0].role).toBe('user')
    expect(messages[0].content).toBe('随便说点什么')
    expect(messages[1].role).toBe('agent')
    expect(messages[1].blocks).toBeDefined()
    expect(messages[1].blocks!.length).toBeGreaterThan(0)
  })

  it('does not send while streaming', async () => {
    useChatStore.setState({ isStreaming: true })

    const store = useChatStore.getState()
    await store.sendMessage('hello')

    expect(useChatStore.getState().messages).toHaveLength(0)
  })
})
