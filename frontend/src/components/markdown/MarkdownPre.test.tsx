import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MarkdownPre } from './MarkdownPre'

describe('MarkdownPre', () => {
  it('renders code block with background', () => {
    const { container } = render(
      <MarkdownPre>
        <code className="language-python">print('hello')</code>
      </MarkdownPre>
    )
    const pre = container.querySelector('pre')!
    expect(pre.style.backgroundColor).toBe('rgb(246, 248, 250)')
    expect(pre.style.borderRadius).toBe('8px')
  })

  it('shows language label when className has language- prefix', () => {
    render(
      <MarkdownPre>
        <code className="language-python">print('hello')</code>
      </MarkdownPre>
    )
    expect(screen.getByText('python')).toBeInTheDocument()
  })

  it('does not show language label without language- prefix', () => {
    const { container } = render(
      <MarkdownPre>
        <code>plain text</code>
      </MarkdownPre>
    )
    expect(container.querySelector('.lang-label')).toBeNull()
  })

  it('copy button writes to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    render(
      <MarkdownPre>
        <code>copy me</code>
      </MarkdownPre>
    )

    const button = screen.getByTitle('Copy code')
    await fireEvent.click(button)
    expect(writeText).toHaveBeenCalledWith('copy me')
  })

  it('handles clipboard failure gracefully', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('not allowed'))
    Object.assign(navigator, { clipboard: { writeText } })

    render(
      <MarkdownPre>
        <code>copy me</code>
      </MarkdownPre>
    )

    // H-FE1: 失败时 writeText 仍被调用，不抛中断；copied 保持 false（未成功）
    await fireEvent.click(screen.getByTitle('Copy code'))
    await new Promise((r) => setTimeout(r, 10))
    expect(writeText).toHaveBeenCalledWith('copy me')
    expect(screen.getByTitle('Copy code').textContent).toBe('Copy')
  })
})
