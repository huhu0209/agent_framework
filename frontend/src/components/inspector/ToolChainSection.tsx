import { useState } from 'react'
import type { ToolCallEntry } from '../../types'

export function ToolChainSection({ toolCalls }: { toolCalls: ToolCallEntry[] }) {
  if (toolCalls.length === 0) return <div className="text-sm" style={{ color: 'var(--text-3)' }}>尚无工具调用</div>
  return (
    <div className="space-y-1.5">
      {toolCalls.map((tc, i) => <ToolItem key={tc.tool_call_id || i} tc={tc} />)}
    </div>
  )
}

function ToolItem({ tc }: { tc: ToolCallEntry }) {
  const [open, setOpen] = useState(false)
  const sourceColor = tc.source === 'mcp' ? 'var(--brand)' : tc.source === 'agent' ? 'var(--warning, #d97706)' : 'var(--text-3)'
  return (
    <div className="border rounded text-sm" style={{ borderColor: 'var(--border)' }}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 px-2 py-1.5">
        <span className="text-xs font-mono" style={{ color: 'var(--text-3)' }}>#{tc.step ?? '·'}</span>
        <span className="font-mono font-medium" style={{ color: 'var(--text)' }}>{tc.tool_name}</span>
        <span className="text-xs px-1 rounded" style={{ backgroundColor: 'var(--sand)', color: sourceColor }}>{tc.source ?? 'builtin'}</span>
        {tc.content !== undefined && <span className="text-xs ml-auto" style={{ color: 'var(--text-3)' }}>✓</span>}
      </button>
      {open && (
        <div className="px-2 pb-2 space-y-1 text-xs font-mono">
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
  )
}
