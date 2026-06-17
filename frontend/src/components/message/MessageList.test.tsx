import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList } from './MessageList'
import { useChatStore } from '../../store'

describe('MessageList', () => {
  beforeEach(() => {
    useChatStore.setState({ messages: [], streamingMessage: null, switchingSession: false })
  })
  it('无消息时渲染空状态', () => {
    render(<MessageList />)
    expect(screen.getByText('今天想探索什么？')).toBeInTheDocument()
  })
})
