import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'
import type { AgentBlock } from '../types'
import { MarkdownTable } from './markdown/MarkdownTable'
import { MarkdownPre } from './markdown/MarkdownPre'
import { MarkdownAnchor } from './markdown/MarkdownAnchor'

export function TextResponseBlock({ block }: { block: AgentBlock }) {
  if (block.kind !== 'text_response') return null

  return (
    <div
      className="prose prose-sm max-w-none
        prose-headings:font-serif prose-headings:text-[var(--text-primary)]
        prose-p:my-1.5
        prose-headings:mt-3 prose-headings:mb-1.5
        prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0
        prose-blockquote:my-1.5
        prose-pre:my-1.5
        prose-table:my-1.5
        prose-a:text-[var(--accent-coral)]
        prose-code:text-[var(--accent-terracotta)]
        prose-blockquote:border-[var(--accent-terracotta)]
        prose-blockquote:text-[var(--text-secondary)]
        prose-pre:bg-[#f6f8fa]"
      style={{ color: 'var(--text-primary)', lineHeight: '1.6' }}
    >
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          table: MarkdownTable,
          pre: MarkdownPre,
          a: MarkdownAnchor,
        }}
      >
        {block.text}
      </Markdown>
    </div>
  )
}
