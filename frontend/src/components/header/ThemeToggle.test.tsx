import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeToggle } from './ThemeToggle'
import { useChatStore } from '../../store'

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    useChatStore.setState({ theme: 'light' })
  })
  it('light 态渲染切换按钮', () => {
    render(<ThemeToggle />)
    expect(screen.getByRole('button', { name: '切换主题' })).toBeInTheDocument()
  })
  it('点击切换到 dark 并持久化', async () => {
    const user = userEvent.setup()
    render(<ThemeToggle />)
    await user.click(screen.getByRole('button', { name: '切换主题' }))
    expect(useChatStore.getState().theme).toBe('dark')
    expect(localStorage.getItem('chat-theme')).toBe('dark')
  })
})
