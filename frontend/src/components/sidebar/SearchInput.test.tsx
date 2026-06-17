import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchInput } from './SearchInput'
import { useChatStore } from '../../store'

describe('SearchInput', () => {
  beforeEach(() => useChatStore.setState({ searchQuery: '' }))
  it('输入更新 store.searchQuery', async () => {
    const user = userEvent.setup()
    render(<SearchInput />)
    await user.type(screen.getByPlaceholderText('搜索对话'), 'glm')
    expect(useChatStore.getState().searchQuery).toBe('glm')
  })
})
