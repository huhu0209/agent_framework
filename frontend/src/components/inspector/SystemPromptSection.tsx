import { useState } from 'react'
import { CaretDown } from '@phosphor-icons/react'
import type { PromptBlockPayload, SystemPromptPayload } from '../../types'

export function SystemPromptSection({ sp, offline }: { sp: SystemPromptPayload | null; offline?: boolean }) {
  const [showText, setShowText] = useState(false)
  if (offline && !sp) {
    return <div className="text-sm" style={{ color: 'var(--text-3)' }}>观测面板离线，实时数据暂停。</div>
  }
  if (!sp) return <div className="text-sm" style={{ color: 'var(--text-3)' }}>等待 system_prompt…</div>
  return (
    <div className="space-y-2.5 text-sm">
      <button onClick={() => setShowText(!showText)}
        className="inline-flex items-center gap-1 text-xs font-medium"
        style={{ color: 'var(--brand)' }}>
        <CaretDown size={12} style={{ transition: 'transform .2s', transform: showText ? 'rotate(0deg)' : 'rotate(-90deg)' }} />
        {showText ? '隐藏' : '显示'}完整 prompt（{sp.text.length} 字）
      </button>
      {showText && (
        <pre className="text-xs whitespace-pre-wrap break-words p-2.5 rounded-md overflow-auto max-h-60 font-mono"
          style={{ backgroundColor: 'var(--sand)', color: 'var(--text-2)' }}>{sp.text}</pre>
      )}
      <div className="pt-1">
        <div className="text-[11px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-3)' }}>组成块（{sp.blocks.length}）</div>
        {sp.blocks.length === 0 && <div className="text-xs" style={{ color: 'var(--text-3)' }}>无 profile，未拆分块</div>}
        <div className="space-y-1.5">
          {sp.blocks.map((b) => <BlockItem key={b.name} block={b} />)}
        </div>
      </div>
    </div>
  )
}

function BlockItem({ block }: { block: PromptBlockPayload }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-md overflow-hidden" style={{ backgroundColor: 'var(--sand)' }}>
      <button onClick={() => setOpen(!open)} className="w-full flex justify-between items-center gap-2 px-2.5 py-1.5 text-xs"
        title={`${block.source} · ${block.stability}`}>
        <span className="font-mono font-medium" style={{ color: 'var(--text)' }}>{block.name}</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded font-mono shrink-0"
          style={{ backgroundColor: 'var(--surface-2)', color: 'var(--text-3)' }}>{block.source}</span>
      </button>
      {open && (
        <pre className="text-xs whitespace-pre-wrap break-words px-2.5 pb-2 max-h-40 overflow-auto font-mono"
          style={{ color: 'var(--text-2)' }}>{block.content}</pre>
      )}
    </div>
  )
}
