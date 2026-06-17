import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MarkdownPre } from './MarkdownPre'

function mockClipboard(writeText: ReturnType<typeof vi.fn>) {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
    writable: true,
  })
}

describe('MarkdownPre', () => {
  it('renders code block with dark background', () => {
    const { container } = render(
      <MarkdownPre>
        <code className="language-python">print('hello')</code>
      </MarkdownPre>
    )
    const pre = container.querySelector('pre')!
    expect(pre).toBeInTheDocument()
    // 深色代码块：背景色由 --code-bg 控制（atom-one-dark），文本为浅色
    expect(pre.style.color).toBe('rgb(227, 225, 216)')
  })

  it('shows language label when className has language- prefix', () => {
    render(
      <MarkdownPre>
        <code className="language-python">print('hello')</code>
      </MarkdownPre>
    )
    expect(screen.getByText('python')).toBeInTheDocument()
  })

  it('falls back to "text" label without language- prefix', () => {
    render(
      <MarkdownPre>
        <code>plain text</code>
      </MarkdownPre>
    )
    expect(screen.getByText('text')).toBeInTheDocument()
  })

  it('copy button writes to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    mockClipboard(writeText)

    render(
      <MarkdownPre>
        <code>copy me</code>
      </MarkdownPre>
    )

    const button = screen.getByRole('button', { name: '复制代码' })
    await fireEvent.click(button)
    expect(writeText).toHaveBeenCalledWith('copy me')
  })

  it('handles clipboard failure gracefully', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('not allowed'))
    mockClipboard(writeText)

    render(
      <MarkdownPre>
        <code>copy me</code>
      </MarkdownPre>
    )

    await fireEvent.click(screen.getByRole('button', { name: '复制代码' }))
    await new Promise((r) => setTimeout(r, 10))
    expect(writeText).toHaveBeenCalledWith('copy me')
    // 失败时按钮文案仍为“复制”
    expect(screen.getByRole('button', { name: '复制代码' }).textContent).toBe('复制')
  })
})
