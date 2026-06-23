import { useChatStore, type ViewName } from '../../store'

const VIEWS: { id: ViewName; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'agent', label: 'Agent' },
  { id: 'teammate', label: 'Teammate' },
  { id: 'orchestrator', label: 'Orchestrator' },
]

export function ViewSwitcher() {
  const activeView = useChatStore((s) => s.activeView)
  const setActiveView = useChatStore((s) => s.setActiveView)
  return (
    <div
      className="inline-flex items-center gap-1 p-1 rounded-lg"
      style={{ backgroundColor: 'var(--sand)' }}
    >
      {VIEWS.map((v) => {
        const active = v.id === activeView
        return (
          <button
            key={v.id}
            onClick={() => setActiveView(v.id)}
            className="px-3 py-1 rounded-md text-[13px] font-medium transition-colors"
            style={{
              backgroundColor: active ? 'var(--surface)' : 'transparent',
              color: active ? 'var(--text)' : 'var(--text-3)',
              cursor: 'pointer',
            }}
            aria-pressed={active}
          >
            {v.label}
          </button>
        )
      })}
    </div>
  )
}
