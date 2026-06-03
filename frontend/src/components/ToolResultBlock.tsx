import { useState } from 'react'
import type { AgentBlock } from '../types'

const MAX_RESULT_DISPLAY = 300

export function ToolResultBlock({ block }: { block: AgentBlock }) {
  const [expanded, setExpanded] = useState(false)
  if (block.kind !== 'tool_result') return null

  const needsTruncation = block.content.length > MAX_RESULT_DISPLAY
  const displayText = expanded || !needsTruncation
    ? block.content
    : block.content.slice(0, MAX_RESULT_DISPLAY) + '…'

  return (
    <div className="rounded-lg px-3 py-2 text-sm leading-relaxed"
      style={{
        backgroundColor: 'var(--bg-parchment)',
        color: 'var(--text-secondary)',
      }}>
      <pre className="whitespace-pre-wrap break-words"
        style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}>
        {displayText}
      </pre>
      {needsTruncation && (
        <button className="text-xs mt-1 hover:underline"
          style={{ color: 'var(--accent-coral)' }}
          onClick={() => setExpanded(!expanded)}>
          {expanded ? '收起' : '展开'}
        </button>
      )}
    </div>
  )
}
