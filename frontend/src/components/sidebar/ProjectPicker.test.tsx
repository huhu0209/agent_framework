import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ProjectPicker } from './ProjectPicker'

describe('ProjectPicker', () => {
  it('lists subdirs from /fs/list and confirm picks current dir', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ name: 'projA', path: '/root/projA' }, { name: 'projB', path: '/root/projB' }],
    })
    vi.stubGlobal('fetch', fetchMock)
    const onPick = vi.fn()
    render(<ProjectPicker rootPath="/root" onPick={onPick} onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('projA')).toBeTruthy())
    fireEvent.click(screen.getByText('选择'))
    expect(onPick).toHaveBeenCalledWith('/root')
    vi.restoreAllMocks()
  })

  it('double-clicking a subdir picks it', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ name: 'projA', path: '/root/projA' }],
    })
    vi.stubGlobal('fetch', fetchMock)
    const onPick = vi.fn()
    render(<ProjectPicker rootPath="/root" onPick={onPick} onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('projA')).toBeTruthy())
    fireEvent.doubleClick(screen.getByText('projA'))
    expect(onPick).toHaveBeenCalledWith('/root/projA')
    vi.restoreAllMocks()
  })
})
