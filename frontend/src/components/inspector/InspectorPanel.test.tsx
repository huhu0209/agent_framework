import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InspectorPanel } from './InspectorPanel'
import { useChatStore } from '../../store'

function setState(patch: Partial<ReturnType<typeof useChatStore.getState>>) {
  useChatStore.setState(patch)
}

describe('InspectorPanel', () => {
  it('关闭时不渲染', () => {
    setState({ inspectorOpen: false })
    const { container } = render(<InspectorPanel />)
    expect(container.firstChild).toBeNull()
  })

  it('离线且无 config 显示降级文案与离线徽章', () => {
    setState({
      inspectorOpen: true,
      wsStatus: 'disconnected',
      inspector: { config: null, systemPrompt: null, toolCalls: [], usage: null },
    })
    render(<InspectorPanel />)
    expect(screen.getAllByText(/观测面板离线/).length).toBeGreaterThan(0)
    expect(screen.getByText('离线')).toBeDefined()
  })

  it('已连接且有 config 显示模型与已连接徽章', () => {
    setState({
      inspectorOpen: true,
      wsStatus: 'connected',
      inspector: {
        config: { model: 'stub-model', max_steps: 5, profile: null, permission_mode: null, tools: ['search'] },
        systemPrompt: null,
        toolCalls: [],
        usage: null,
      },
    })
    render(<InspectorPanel />)
    expect(screen.getByText('stub-model')).toBeDefined()
    expect(screen.getByText('已连接')).toBeDefined()
  })

  it('显示用量 section 标题', () => {
    setState({
      inspectorOpen: true,
      wsStatus: 'connected',
      inspector: { config: null, systemPrompt: null, toolCalls: [], usage: null },
    })
    render(<InspectorPanel />)
    expect(screen.getByText('用量')).toBeDefined()
  })
})
