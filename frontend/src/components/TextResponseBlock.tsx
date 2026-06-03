import type { AgentBlock } from '../types'

export function TextResponseBlock({ block }: { block: AgentBlock }) {
  if (block.kind !== 'text_response') return null

  const html = block.text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^## (.+)$/gm, '<h2 class="text-base font-semibold mt-3 mb-1">$1</h2>')
    .replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold mt-2 mb-1">$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
    .replace(/\n/g, '<br />')

  return (
    <div className="text-base leading-relaxed"
      style={{ color: 'var(--text-primary)', lineHeight: '1.6' }}
      dangerouslySetInnerHTML={{ __html: html }} />
  )
}
