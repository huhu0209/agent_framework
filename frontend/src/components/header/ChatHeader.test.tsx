import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatHeader } from './ChatHeader'

describe('ChatHeader', () => {
  it('渲染模型名与操作按钮', () => {
    render(<ChatHeader />)
    expect(screen.getByText('GLM-5.2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '切换主题' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '分享' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '更多' })).toBeInTheDocument()
  })
})
