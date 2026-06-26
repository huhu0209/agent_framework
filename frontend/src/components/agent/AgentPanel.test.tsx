import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useChatStore } from '../../store'
import { AgentPanel } from './AgentPanel'

describe('AgentPanel', () => {
  beforeEach(() => {
    useChatStore.setState({
      agents: [], activeAgentName: null, skills: [],
      loadAgents: vi.fn().mockResolvedValue(undefined),
      loadSkills: vi.fn().mockResolvedValue(undefined),
      createAgent: vi.fn().mockResolvedValue(undefined),
    })
  })

  it('挂载时拉取 agents 与 skills', () => {
    render(<AgentPanel />)
    expect(useChatStore.getState().loadAgents).toHaveBeenCalled()
    expect(useChatStore.getState().loadSkills).toHaveBeenCalled()
  })

  it('渲染空列表提示', () => {
    render(<AgentPanel />)
    expect(screen.getByText(/暂无 agent/i)).toBeInTheDocument()
  })

  it('点击新建后调 createAgent', async () => {
    const user = userEvent.setup()
    render(<AgentPanel />)
    await user.click(screen.getByRole('button', { name: /新建 agent/i }))
    await user.type(screen.getByLabelText(/名字/i), 'reviewer')
    await user.click(screen.getByRole('button', { name: /保存/i }))
    expect(useChatStore.getState().createAgent).toHaveBeenCalled()
  })
})
