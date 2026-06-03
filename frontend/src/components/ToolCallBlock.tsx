import { useState } from 'react'
import type { AgentBlock } from '../types'

const MAX_PARAMS_DISPLAY = 200

export function ToolCallBlock({ block }: { block: AgentBlock }) {
  const [expanded, setExpanded] = useState(false)
  if (block.kind !== 'tool_call') return null

  const json = JSON.stringify(block.params, null, 2)
  const needsTruncation = json.length > MAX_PARAMS_DISPLAY
  const displayText = expanded || !needsTruncation
    ? json
    : json.slice(0, MAX_PARAMS_DISPLAY) + '…'

  return (
    <div className="flex gap-2.5 pl-1">
      <div className="w-0.5 shrink-0 rounded-full"
        style={{ backgroundColor: 'var(--accent-terracotta)' }} />
      <div className="min-w-0 flex-1">
        <div className="font-mono text-sm" style={{ color: 'var(--accent-terracotta)' }}>
          {block.toolName}
        </div>
        <pre className="mt-1 text-xs leading-relaxed whitespace-pre-wrap break-all"
          style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {displayText}
        </pre>
        {needsTruncation && (
          <button className="text-xs mt-0.5 hover:underline"
            style={{ color: 'var(--accent-coral)' }}
            onClick={() => setExpanded(!expanded)}>
            {expanded ? '收起' : '展开'}
          </button>
        )}
      </div>
    </div>
  )
}
