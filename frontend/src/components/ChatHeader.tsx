import { useChatStore } from '../store'

export function ChatHeader() {
  const agentName = useChatStore((s) => s.agentName)

  return (
    <header className="flex items-center justify-between px-5 py-3"
      style={{ backgroundColor: 'var(--bg-ivory)', borderBottom: '1px solid var(--border-cream)' }}>
      <span className="text-lg font-medium" style={{ fontFamily: 'var(--font-serif)' }}>
        {agentName}
      </span>
      <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full"
        style={{
          backgroundColor: 'var(--surface-sand)',
          color: 'var(--text-tertiary)',
        }}>
        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
        Connected
      </span>
    </header>
  )
}
