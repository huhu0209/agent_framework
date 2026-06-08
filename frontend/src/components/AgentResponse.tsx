import type { AgentBlock, ChatMessage } from '../types'
import { ThinkingBlock } from './ThinkingBlock'
import { ToolCallBlock } from './ToolCallBlock'
import { TextResponseBlock } from './TextResponseBlock'

function groupBlocks(blocks: AgentBlock[]) {
  const grouped: { block: AgentBlock; result?: AgentBlock }[] = []
  const paired = new Set<string>()

  for (let i = 0; i < blocks.length; i++) {
    if (paired.has(blocks[i].id)) continue

    if (blocks[i].kind === 'tool_call') {
      const next = blocks[i + 1]
      const result = next?.kind === 'tool_result' ? next : undefined
      if (result) paired.add(result.id)
      grouped.push({ block: blocks[i], result })
    } else {
      grouped.push({ block: blocks[i] })
    }
  }

  return grouped
}

export function AgentResponse({ message }: { message: ChatMessage }) {
  const blocks = message.blocks ?? []
  const grouped = groupBlocks(blocks)

  return (
    <div className="max-w-[85%] rounded-xl px-4 py-3"
      style={{
        backgroundColor: 'var(--bg-ivory)',
        border: '1px solid var(--border-cream)',
      }}>
      {blocks.length === 0 && (
        <div className="flex items-center gap-2 text-sm"
          style={{ color: 'var(--text-tertiary)' }}>
          <span className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ backgroundColor: 'var(--accent-terracotta)' }} />
          正在思考…
        </div>
      )}
      <div className="flex flex-col gap-2.5">
        {grouped.map(({ block, result }) => {
          switch (block.kind) {
            case 'thinking':
              return <ThinkingBlock key={block.id} block={block} />
            case 'tool_call':
              return <ToolCallBlock key={block.id} block={block} result={result} />
            case 'tool_result':
              return <ToolCallBlock key={block.id} block={block} />
            case 'text_response':
              return <TextResponseBlock key={block.id} block={block} />
            case 'error':
              return (
                <div key={block.id} className="text-sm px-3 py-2 rounded-lg"
                  style={{ backgroundColor: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' }}>
                  ⚠ {block.text}
                </div>
              )
          }
        })}
      </div>
    </div>
  )
}
