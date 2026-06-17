import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SessionSidebar } from './SessionSidebar'
import { useChatStore } from '../../store'
import type { SessionInfo } from '../../types'

const DAY = 86400

describe('SessionSidebar', () => {
  beforeEach(() => {
    useChatStore.setState({ sessions: [], sessionId: null, sessionsLoading: false, searchQuery: '', sidebarOpen: true })
  })
  it('按时间分组渲染会话', () => {
    const now = Date.now() / 1000
    const sessions: SessionInfo[] = [
      { session_id: '1', title: '今天的', created_at: now - 100 },
      { session_id: '2', title: '昨天的', created_at: now - DAY - 100 },
      { session_id: '3', title: '更早的', created_at: now - 10 * DAY },
    ]
    useChatStore.setState({ sessions })
    render(<SessionSidebar />)
    expect(screen.getByText('今天')).toBeInTheDocument()
    expect(screen.getByText('昨天')).toBeInTheDocument()
    expect(screen.getByText('更早')).toBeInTheDocument()
    expect(screen.getByText('今天的')).toBeInTheDocument()
  })
  it('搜索过滤会话', async () => {
    const user = userEvent.setup()
    useChatStore.setState({
      sessions: [
        { session_id: '1', title: 'LLM Adapter', created_at: 1 },
        { session_id: '2', title: 'Tool System', created_at: 2 },
      ],
    })
    render(<SessionSidebar />)
    await user.type(screen.getByPlaceholderText('搜索对话'), 'adapter')
    expect(screen.getByText('LLM Adapter')).toBeInTheDocument()
    expect(screen.queryByText('Tool System')).not.toBeInTheDocument()
  })
})
