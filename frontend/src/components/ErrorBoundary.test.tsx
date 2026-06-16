import { describe, it, expect, vi } from 'vitest'
import { type ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

function Thrower({ msg }: { msg: string }): ReactNode {
  throw new Error(msg)
}

describe('ErrorBoundary', () => {
  it('catches render error and shows fallback UI', () => {
    // 抑制 React 控制台错误日志（预期内的渲染错误）
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Thrower msg="boom" />
      </ErrorBoundary>,
    )
    // H-FE4: 捕获异常，显示 fallback（不白屏）
    expect(screen.getByText('出错了')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '刷新页面' })).toBeInTheDocument()
    spy.mockRestore()
  })

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>healthy child</div>
      </ErrorBoundary>,
    )
    expect(screen.getByText('healthy child')).toBeInTheDocument()
  })
})
