import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UsageSection } from './UsageSection'
import type { UsageState } from '../../types'

const usage: UsageState = {
  input: 1000, output: 200,
  cumulative_input: 3000, cumulative_output: 600,
  max_context: 200000,
}

describe('UsageSection', () => {
  it('无 usage 且在线显示等待文案', () => {
    render(<UsageSection usage={null} />)
    expect(screen.getByText('等待首次调用…')).toBeDefined()
  })

  it('离线且无 usage 显示离线文案', () => {
    render(<UsageSection usage={null} offline />)
    expect(screen.getByText(/观测面板离线/)).toBeDefined()
  })

  it('有 usage 渲染当前/上限、占比、本次与累计', () => {
    render(<UsageSection usage={usage} />)
    expect(screen.getByText('1,000 / 200,000')).toBeDefined()
    expect(screen.getByText('0.50%')).toBeDefined()
    expect(screen.getByText(/↑ 1,000/)).toBeDefined()   // 本次 input
    expect(screen.getByText(/↑ 3,000/)).toBeDefined()   // 累计 input
  })

  it('占比超阈值时进度条标记警戒态', () => {
    const heavy: UsageState = { ...usage, input: 180000, max_context: 200000 } // 90%
    const { container } = render(<UsageSection usage={heavy} />)
    const bar = container.querySelector('[data-testid="usage-bar"]') as HTMLElement
    expect(bar.getAttribute('data-warn')).toBe('1')
  })

  it('占比低于阈值时不标记警戒态', () => {
    const { container } = render(<UsageSection usage={usage} />) // 0.5%
    const bar = container.querySelector('[data-testid="usage-bar"]') as HTMLElement
    expect(bar.getAttribute('data-warn')).toBe('0')
  })
})
