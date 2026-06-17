import { List } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function SidebarToggle() {
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)
  const toggleSidebar = useChatStore((s) => s.toggleSidebar)
  if (sidebarOpen) return null
  return (
    <button
      onClick={toggleSidebar}
      className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sand)]"
      style={{ color: 'var(--text-2)' }}
      aria-label="展开侧栏"
      title="展开侧栏"
    >
      <List size={20} />
    </button>
  )
}
