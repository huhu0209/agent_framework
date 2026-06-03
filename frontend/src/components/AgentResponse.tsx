import type { ChatMessage } from '../types'
import { ThinkingBlock } from './ThinkingBlock'
import { ToolCallBlock } from './ToolCallBlock'
import { ToolResultBlock } from './ToolResultBlock'
import { TextResponseBlock } from './TextResponseBlock'

export function AgentResponse({ message }: { message: ChatMessage }) {
  const blocks = message.blocks ?? []

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
        {blocks.map((block, i) => {
          switch (block.kind) {
            case 'thinking':
              return <ThinkingBlock key={i} block={block} />
            case 'tool_call':
              return <ToolCallBlock key={i} block={block} />
            case 'tool_result':
              return <ToolResultBlock key={i} block={block} />
            case 'text_response':
              return <TextResponseBlock key={i} block={block} />
          }
        })}
      </div>
    </div>
  )
}
