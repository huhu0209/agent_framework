import { Sparkle, CaretDown } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function ModelChip() {
  const model = useChatStore((s) => s.inspector.config?.model)
  return (
    <button
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors hover:bg-[var(--sand)]"
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border-2)',
        color: 'var(--text)',
      }}
      aria-label="当前模型"
      title="当前模型"
    >
      <Sparkle size={16} weight="fill" style={{ color: 'var(--brand)' }} />
      {model ?? '—'}
      <CaretDown size={13} style={{ color: 'var(--text-3)' }} />
    </button>
  )
}
