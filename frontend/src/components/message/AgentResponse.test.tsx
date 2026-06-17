import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentResponse } from './AgentResponse'
import type { ChatMessage } from '../../types'

describe('AgentResponse', () => {
  it('无 blocks 时显示 typing 动画', () => {
    const msg: ChatMessage = { id: 'a1', role: 'agent', timestamp: 1, blocks: [] }
    const { container } = render(<AgentResponse message={msg} />)
    expect(container.querySelector('.typing-dots')).toBeInTheDocument()
  })
  it('有 text_response 时渲染文本', () => {
    const msg: ChatMessage = { id: 'a2', role: 'agent', timestamp: 1, blocks: [{ id: 'b1', kind: 'text_response', text: '你好' }] }
    render(<AgentResponse message={msg} />)
    expect(screen.getByText('你好')).toBeInTheDocument()
  })
})
