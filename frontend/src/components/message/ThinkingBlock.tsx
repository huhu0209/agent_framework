import { useState } from 'react'
import { Brain, CaretRight } from '@phosphor-icons/react'
import type { AgentBlock } from '../../types'

export function ThinkingBlock({ block }: { block: AgentBlock }) {
  const [open, setOpen] = useState(false)
  if (block.kind !== 'thinking') return null
  return (
    <div className="rounded-lg overflow-hidden mb-3" style={{ border: '1px solid var(--border-2)', backgroundColor: 'var(--surface)' }}>
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 w-full px-3.5 py-2.5 text-[13.5px] font-medium text-left transition-colors hover:bg-[var(--sand)]" style={{ color: 'var(--text-2)' }} aria-expanded={open}>
        <Brain size={16} style={{ color: 'var(--brand)' }} />
        <span>思考过程</span>
        <CaretRight size={13} className="ml-auto transition-transform" style={{ transform: open ? 'rotate(90deg)' : 'none' }} />
      </button>
      <div style={{ maxHeight: open ? 400 : 0, overflow: 'hidden', transition: 'max-height .25s ease' }}>
        <div className="px-3.5 pb-3 pl-10 text-[13.5px] leading-relaxed italic" style={{ color: 'var(--text-2)' }}>{block.text}</div>
      </div>
    </div>
  )
}
