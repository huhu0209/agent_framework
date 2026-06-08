import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownTable } from './MarkdownTable'

describe('MarkdownTable', () => {
  const basicTable = (
    <MarkdownTable>
      <thead>
        <tr>
          <th>Name</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Foo</td>
          <td>Bar</td>
        </tr>
      </tbody>
    </MarkdownTable>
  )

  it('renders table with scrollable wrapper', () => {
    const { container } = render(basicTable)
    const wrapper = container.firstElementChild as HTMLElement
    expect(wrapper.style.overflowX).toBe('auto')
    expect(wrapper.querySelector('table')).not.toBeNull()
  })

  it('renders header and body cells', () => {
    render(basicTable)
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Foo')).toBeInTheDocument()
  })

  it('table has border-collapse style', () => {
    const { container } = render(basicTable)
    const table = container.querySelector('table')!
    expect(table.style.borderCollapse).toBe('collapse')
  })
})
