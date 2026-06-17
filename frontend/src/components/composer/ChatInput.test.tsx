import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from './ChatInput'
import { useChatStore } from '../../store'

describe('ChatInput', () => {
  beforeEach(() => {
    useChatStore.setState({ isStreaming: false, composerDraft: '' })
  })

  it('输入回车发送', async () => {
    const user = userEvent.setup()
    const send = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({ sendMessage: send })
    render(<ChatInput />)
    await user.type(screen.getByPlaceholderText('给助手发消息'), '你好{Enter}')
    expect(send).toHaveBeenCalledWith('你好')
  })

  it('composerDraft 填入输入框', () => {
    useChatStore.setState({ composerDraft: 'LLM Adapter 支持哪些 provider？' })
    render(<ChatInput />)
    expect(screen.getByDisplayValue('LLM Adapter 支持哪些 provider？')).toBeInTheDocument()
  })
})
