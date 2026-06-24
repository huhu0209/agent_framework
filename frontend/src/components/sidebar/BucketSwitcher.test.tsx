import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BucketSwitcher } from './BucketSwitcher'

vi.mock('../../store', () => ({
  useChatStore: (sel: (s: any) => any) =>
    sel({
      buckets: [
        { bucket: 'default_chat', display_name: 'default_chat' },
        { bucket: 'myapp_abcd1234', display_name: 'myapp' },
      ],
      currentBucket: 'default_chat',
      setCurrentBucket: vi.fn(),
      loadBuckets: vi.fn(),
    } as any),
}))

describe('BucketSwitcher', () => {
  it('renders current bucket as selected value', () => {
    render(<BucketSwitcher />)
    const select = screen.getByLabelText('切换项目桶') as HTMLSelectElement
    expect(select.value).toBe('default_chat')
    expect(screen.getByText('myapp')).toBeTruthy()
  })
})
