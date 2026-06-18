import { useState } from 'react'
import type { PromptBlockPayload, SystemPromptPayload } from '../../types'

export function SystemPromptSection({ sp }: { sp: SystemPromptPayload | null }) {
  const [showText, setShowText] = useState(false)
  if (!sp) return <div className="text-sm" style={{ color: 'var(--text-3)' }}>等待 system_prompt…</div>
  return (
    <div className="space-y-2 text-sm">
      <button onClick={() => setShowText(!showText)} className="text-xs" style={{ color: 'var(--brand)' }}>
        {showText ? '▾ 隐藏' : '▸ 显示'}完整 prompt（{sp.text.length} 字）
      </button>
      {showText && (
        <pre className="text-xs whitespace-pre-wrap break-words p-2 rounded overflow-auto max-h-60 font-mono"
          style={{ backgroundColor: 'var(--sand)', color: 'var(--text-2)' }}>{sp.text}</pre>
      )}
      <div className="text-xs" style={{ color: 'var(--text-3)' }}>组成块（{sp.blocks.length}）</div>
      {sp.blocks.length === 0 && <div className="text-xs" style={{ color: 'var(--text-3)' }}>无 profile，未拆分块</div>}
      {sp.blocks.map((b) => <BlockItem key={b.name} block={b} />)}
    </div>
  )
}

function BlockItem({ block }: { block: PromptBlockPayload }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border rounded" style={{ borderColor: 'var(--border)' }}>
      <button onClick={() => setOpen(!open)} className="w-full flex justify-between px-2 py-1 text-xs">
        <span className="font-mono" style={{ color: 'var(--text)' }}>{block.name}</span>
        <span style={{ color: 'var(--text-3)' }}>{block.source} · {block.stability}</span>
      </button>
      {open && (
        <pre className="text-xs whitespace-pre-wrap break-words px-2 pb-2 max-h-40 overflow-auto font-mono"
          style={{ color: 'var(--text-2)' }}>{block.content}</pre>
      )}
    </div>
  )
}
