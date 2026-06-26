import { useEffect } from 'react'
import { ModelChip } from './ModelChip'
import { SidebarToggle } from './SidebarToggle'
import { InspectButton } from './InspectButton'
import { ViewSwitcher } from './ViewSwitcher'
import { useChatStore } from '../../store'

export function ChatHeader() {
  const activeView = useChatStore((s) => s.activeView)
  const agents = useChatStore((s) => s.agents)
  const currentChatAgent = useChatStore((s) => s.currentChatAgent)
  const setCurrentChatAgent = useChatStore((s) => s.setCurrentChatAgent)
  const loadAgents = useChatStore((s) => s.loadAgents)

  // 挂载即拉 agent 列表，供 chat view 的下拉选择器使用
  useEffect(() => {
    void loadAgents()
  }, [loadAgents])

  return (
    <header
      className="grid grid-cols-3 items-center px-5 py-3"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <div className="flex items-center gap-2">
        {activeView === 'chat' && <SidebarToggle />}
        <ModelChip />
      </div>
      <div className="flex items-center justify-center">
        <ViewSwitcher />
      </div>
      <div className="flex items-center justify-end gap-2">
        {activeView === 'chat' && (
          <select
            value={currentChatAgent ?? ''}
            onChange={(e) => setCurrentChatAgent(e.target.value || null)}
            className="px-2 py-1 rounded-md text-[12px]"
            style={{
              border: '1px solid var(--border)',
              color: 'var(--text-2)',
              backgroundColor: 'var(--surface)',
            }}
            aria-label="选择 agent"
          >
            <option value="">默认 agent</option>
            {agents.map((a) => (
              <option key={a.name} value={a.name}>{a.name}</option>
            ))}
          </select>
        )}
        <InspectButton />
      </div>
    </header>
  )
}
