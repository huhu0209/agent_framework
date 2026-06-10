import { useChatStore } from '../store'

export function SidebarToggle() {
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)
  const toggleSidebar = useChatStore((s) => s.toggleSidebar)

  return (
    <button
      onClick={toggleSidebar}
      className="p-1.5 rounded-lg transition-colors text-[var(--text-secondary)] hover:bg-[var(--surface-sand)]"
      aria-label={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        {sidebarOpen ? (
          <>
            <line x1="4" y1="4" x2="14" y2="4" />
            <line x1="4" y1="9" x2="14" y2="9" />
            <line x1="4" y1="14" x2="14" y2="14" />
            <line x1="14" y1="2" x2="14" y2="16" />
          </>
        ) : (
          <>
            <line x1="2" y1="4" x2="16" y2="4" />
            <line x1="2" y1="9" x2="16" y2="9" />
            <line x1="2" y1="14" x2="16" y2="14" />
          </>
        )}
      </svg>
    </button>
  )
}
