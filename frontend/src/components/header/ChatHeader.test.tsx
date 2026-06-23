import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatHeader } from './ChatHeader'

describe('ChatHeader', () => {
  it('渲染模型名与视图切换器', () => {
    render(<ChatHeader />)
    expect(screen.getByRole('button', { name: '当前模型' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Orchestrator' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Teammate' })).toBeInTheDocument()
  })
})
