import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SuggestCards } from './SuggestCards'
import { useChatStore } from '../../store'

describe('SuggestCards', () => {
  beforeEach(() => useChatStore.setState({ composerDraft: '' }))
  it('点击建议卡片填入 composerDraft', async () => {
    const user = userEvent.setup()
    render(<SuggestCards />)
    await user.click(screen.getByText('LLM Adapter 支持哪些 provider？'))
    expect(useChatStore.getState().composerDraft).toBe('LLM Adapter 支持哪些 provider？')
  })
})
