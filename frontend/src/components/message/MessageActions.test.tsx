import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageActions } from './MessageActions'
import { useChatStore } from '../../store'

function mockClipboard(writeText: ReturnType<typeof vi.fn>) {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
    writable: true,
  })
}

describe('MessageActions', () => {
  it('复制写入剪贴板', async () => {
    const user = userEvent.setup()
    const write = vi.fn().mockResolvedValue(undefined)
    mockClipboard(write)
    render(<MessageActions text="答案" />)
    await user.click(screen.getByRole('button', { name: '复制' }))
    expect(write).toHaveBeenCalledWith('答案')
  })
  it('重新生成调用 sendMessage(上一条 user)', async () => {
    const user = userEvent.setup()
    useChatStore.setState({ messages: [{ id: 'u1', role: 'user', timestamp: 1, content: '上一条问题' }] })
    const send = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({ sendMessage: send })
    render(<MessageActions text="答案" />)
    await user.click(screen.getByRole('button', { name: '重新生成' }))
    expect(send).toHaveBeenCalledWith('上一条问题')
  })
  it('无 user 消息时重新生成不调用 sendMessage', async () => {
    const user = userEvent.setup()
    useChatStore.setState({ messages: [] })
    const send = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({ sendMessage: send })
    render(<MessageActions text="答案" />)
    await user.click(screen.getByRole('button', { name: '重新生成' }))
    expect(send).not.toHaveBeenCalled()
  })
})
