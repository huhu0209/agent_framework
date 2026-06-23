import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import rehypeSanitize from 'rehype-sanitize'
import type { AgentBlock } from '../../types'
import { MarkdownTable } from '../markdown/MarkdownTable'
import { MarkdownPre } from '../markdown/MarkdownPre'
import { MarkdownAnchor } from '../markdown/MarkdownAnchor'

export function TextResponseBlock({ block }: { block: AgentBlock }) {
  if (block.kind !== 'text_response') return null
  return (
    <div
      className="prose prose-sm max-w-none
        prose-headings:font-serif prose-headings:text-[var(--text)]
        prose-p:my-1.5 prose-headings:mt-3 prose-headings:mb-1.5
        prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0
        prose-blockquote:my-1.5 prose-pre:my-1.5 prose-table:my-1.5 prose-hr:my-3
        prose-a:text-[var(--coral)]
        prose-code:text-[var(--brand)]
        prose-blockquote:border-[var(--brand)] prose-hr:border-[var(--border)]
        prose-blockquote:text-[var(--text-2)]"
      style={{ color: 'var(--text)', lineHeight: '1.7', fontSize: '15.5px' }}
    >
      <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight, rehypeSanitize]} components={{ table: MarkdownTable, pre: MarkdownPre, a: MarkdownAnchor }}>
        {block.text}
      </Markdown>
    </div>
  )
}
