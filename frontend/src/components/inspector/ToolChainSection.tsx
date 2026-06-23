import { useState } from 'react'
import { CaretDown } from '@phosphor-icons/react'
import type { ToolCallEntry } from '../../types'

export function ToolChainSection({ toolCalls }: { toolCalls: ToolCallEntry[] }) {
  if (toolCalls.length === 0) return <div className="text-sm" style={{ color: 'var(--text-3)' }}>尚无工具调用</div>
  return (
    <div className="relative space-y-1.5 pl-5">
      <span className="absolute left-[7px] top-1.5 bottom-1.5 w-px" style={{ backgroundColor: 'var(--border-2)' }} />
      {toolCalls.map((tc, i) => <ToolItem key={tc.tool_call_id || i} tc={tc} />)}
    </div>
  )
}

function ToolItem({ tc }: { tc: ToolCallEntry }) {
  const [open, setOpen] = useState(false)
  const sourceColor = tc.source === 'mcp' ? 'var(--brand)' : tc.source === 'agent' ? 'var(--coral)' : 'var(--text-3)'
  return (
    <div className="relative">
      <span className="absolute -left-5 top-2 w-3.5 h-3.5 rounded-full inline-flex items-center justify-center text-[9px] font-bold font-mono"
        style={{ backgroundColor: 'var(--brand)', color: 'var(--ivory)', boxShadow: '0 0 0 2px var(--surface-2)' }}>
        {tc.step ?? '·'}
      </span>
      <div className="rounded-md" style={{ backgroundColor: 'var(--sand)' }}>
        <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 px-2.5 py-1.5">
          <span className="font-mono font-medium text-[13px]" style={{ color: 'var(--text)' }}>{tc.tool_name}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded font-mono"
            style={{ backgroundColor: 'var(--surface-2)', color: sourceColor }}>{tc.source ?? 'builtin'}</span>
          <span className="ml-auto flex items-center gap-1.5">
            {tc.content !== undefined && <span className="text-xs" style={{ color: 'var(--success)' }}>✓</span>}
            <CaretDown size={12} style={{ color: 'var(--text-3)', transition: 'transform .2s', transform: open ? 'rotate(0deg)' : 'rotate(-90deg)' }} />
          </span>
        </button>
        {open && (
          <div className="px-2.5 pb-2 space-y-1 text-xs font-mono">
            <div style={{ color: 'var(--text-3)' }}>参数:</div>
            <pre className="whitespace-pre-wrap break-words" style={{ color: 'var(--text-2)' }}>{JSON.stringify(tc.params, null, 2)}</pre>
            {tc.content !== undefined && (
              <>
                <div style={{ color: 'var(--text-3)' }}>结果:</div>
                <pre className="whitespace-pre-wrap break-words max-h-40 overflow-auto" style={{ color: 'var(--text-2)' }}>{tc.content}</pre>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
