import { ShareNetwork, DotsThree } from '@phosphor-icons/react'
import { ModelChip } from './ModelChip'
import { ThemeToggle } from './ThemeToggle'
import { SidebarToggle } from './SidebarToggle'

export function ChatHeader() {
  return (
    <header
      className="flex items-center justify-between px-5 py-3"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <div className="flex items-center gap-2">
        <SidebarToggle />
        <ModelChip />
      </div>
      <div className="flex items-center gap-1">
        <ThemeToggle />
        <button
          className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sand)]"
          style={{ color: 'var(--text-2)' }}
          aria-label="分享"
          title="分享"
        >
          <ShareNetwork size={20} />
        </button>
        <button
          className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sand)]"
          style={{ color: 'var(--text-2)' }}
          aria-label="更多"
          title="更多"
        >
          <DotsThree size={22} weight="bold" />
        </button>
      </div>
    </header>
  )
}
