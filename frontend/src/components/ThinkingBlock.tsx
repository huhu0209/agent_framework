import { useState } from 'react'
import type { AgentBlock } from '../types'

export function ThinkingBlock({ block }: { block: AgentBlock }) {
  const [collapsed, setCollapsed] = useState(true)
  if (block.kind !== 'thinking') return null

  return (
    <div className="cursor-pointer select-none"
      onClick={() => setCollapsed(!collapsed)}
      role="button"
      tabIndex={0}
      aria-expanded={!collapsed}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setCollapsed(!collapsed) }}>
      <div className="flex items-center gap-1.5 text-sm"
        style={{ color: 'var(--text-tertiary)' }}>
        <svg className={`w-3.5 h-3.5 transition-transform ${collapsed ? '' : 'rotate-90'}`}
          fill="currentColor" viewBox="0 0 20 20">
          <path d="M6 4l8 6-8 6V4z" />
        </svg>
        <span>{collapsed ? '思考中…' : '思考过程'}</span>
      </div>
      {!collapsed && (
        <p className="mt-1.5 ml-5 text-sm leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          {block.text}
        </p>
      )}
    </div>
  )
}
