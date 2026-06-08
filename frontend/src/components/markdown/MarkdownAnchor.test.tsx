import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownAnchor } from './MarkdownAnchor'

describe('MarkdownAnchor', () => {
  it('renders link with target blank and security rel', () => {
    render(<MarkdownAnchor href="https://example.com">click me</MarkdownAnchor>)
    const link = screen.getByRole('link', { name: /click me/i })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('href', 'https://example.com')
  })

  it('renders external link icon after text', () => {
    render(<MarkdownAnchor href="https://example.com">link</MarkdownAnchor>)
    const svg = document.querySelector('svg')
    expect(svg).not.toBeNull()
  })

  it('applies coral accent color style', () => {
    render(<MarkdownAnchor href="https://example.com">link</MarkdownAnchor>)
    const link = screen.getByRole('link')
    expect(link.style.color).toBe('var(--accent-coral)')
  })
})
