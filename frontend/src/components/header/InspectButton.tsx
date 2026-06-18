import { Binoculars } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function InspectButton() {
  const open = useChatStore((s) => s.inspectorOpen)
  const toggle = useChatStore((s) => s.toggleInspector)
  return (
    <button
      onClick={toggle}
      className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sand)]"
      style={{ color: open ? 'var(--brand)' : 'var(--text-2)' }}
      aria-label="观测面板"
      title="观测面板"
    >
      <Binoculars size={20} />
    </button>
  )
}
