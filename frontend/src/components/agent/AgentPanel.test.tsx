import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useChatStore } from '../../store'
import { AgentPanel } from './AgentPanel'
import type { AgentDetail } from '../../types'

const detail = (name: string, soul: string): AgentDetail => ({
  name, description: '', model: null, skills: null, tools: null,
  permission_mode: 'ask', soul, identity: '', agents_rules: '', tool_guidance: '',
})

describe('AgentPanel', () => {
  beforeEach(() => {
    useChatStore.setState({
      agents: [], activeAgentName: null, skills: [],
      loadAgents: vi.fn().mockResolvedValue(undefined),
      loadSkills: vi.fn().mockResolvedValue(undefined),
      createAgent: vi.fn().mockResolvedValue(undefined),
      getAgent: vi.fn().mockResolvedValue(null),
      deleteAgent: vi.fn().mockResolvedValue(undefined),
      setActiveAgentName: vi.fn(),
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

  it('快速切换 agent 时,旧 promise 后 resolve 不覆盖新 draft(LOW#5)', async () => {
    const resolvers: Record<string, (v: AgentDetail | null) => void> = {}
    const getAgent = vi.fn((name: string) => new Promise<AgentDetail | null>((res) => {
      resolvers[name] = res
    }))
    useChatStore.setState({
      agents: [{ name: 'a', description: '' }, { name: 'b', description: '' }],
      activeAgentName: null, skills: [],
      loadAgents: vi.fn().mockResolvedValue(undefined),
      loadSkills: vi.fn().mockResolvedValue(undefined),
      getAgent,
      deleteAgent: vi.fn().mockResolvedValue(undefined),
      setActiveAgentName: (name: string | null) => { useChatStore.setState({ activeAgentName: name }) },
    })
    const user = userEvent.setup()
    render(<AgentPanel />)
    // 快切 a → b
    await user.click(screen.getByRole('button', { name: 'a' }))
    await user.click(screen.getByRole('button', { name: 'b' }))
    // b 先 resolve → draft = b
    await act(async () => { resolvers['b'](detail('b', 'b-soul')) })
    expect(screen.getByDisplayValue('b-soul')).toBeInTheDocument()
    // a 后 resolve → guard 拦截,draft 仍为 b
    await act(async () => { resolvers['a'](detail('a', 'a-soul')) })
    expect(screen.queryByDisplayValue('a-soul')).not.toBeInTheDocument()
    expect(screen.getByDisplayValue('b-soul')).toBeInTheDocument()
  })

  it('删除 agent 需两步确认(LOW#9)', async () => {
    const deleteAgent = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({
      agents: [{ name: 'a', description: '' }], activeAgentName: 'a', skills: [],
      loadAgents: vi.fn().mockResolvedValue(undefined),
      loadSkills: vi.fn().mockResolvedValue(undefined),
      getAgent: vi.fn().mockResolvedValue(detail('a', 'a-soul')),
      deleteAgent,
      setActiveAgentName: vi.fn(),
    })
    const user = userEvent.setup()
    render(<AgentPanel />)
    await screen.findByDisplayValue('a')
    // 点删除 → 进入确认态(不直接调 deleteAgent)
    await user.click(screen.getByRole('button', { name: '删除' }))
    expect(deleteAgent).not.toHaveBeenCalled()
    // 点确认删除
    await user.click(screen.getByRole('button', { name: '确认删除' }))
    expect(deleteAgent).toHaveBeenCalledWith('a')
  })
})
