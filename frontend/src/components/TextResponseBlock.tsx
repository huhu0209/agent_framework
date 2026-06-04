import Markdown from 'react-markdown'
import type { AgentBlock } from '../types'

export function TextResponseBlock({ block }: { block: AgentBlock }) {
  if (block.kind !== 'text_response') return null

  return (
    <div className="text-base leading-relaxed prose prose-sm max-w-none"
      style={{ color: 'var(--text-primary)', lineHeight: '1.6' }}>
      <Markdown>{block.text}</Markdown>
    </div>
  )
}
