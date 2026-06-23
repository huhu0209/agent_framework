import { ModelChip } from './ModelChip'
import { SidebarToggle } from './SidebarToggle'
import { InspectButton } from './InspectButton'
import { ViewSwitcher } from './ViewSwitcher'
import { useChatStore } from '../../store'

export function ChatHeader() {
  const activeView = useChatStore((s) => s.activeView)
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
      <div className="flex items-center justify-end">
        <InspectButton />
      </div>
    </header>
  )
}
