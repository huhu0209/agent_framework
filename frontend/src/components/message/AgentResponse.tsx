import { lazy, Suspense } from 'react'
import { Sparkle } from '@phosphor-icons/react'
import type { AgentBlock, ChatMessage } from '../../types'
import { ThinkingBlock } from './ThinkingBlock'
import { ToolCallBlock } from './ToolCallBlock'
import { MessageActions } from './MessageActions'

// markdown 渲染管线重（react-markdown + remark-gfm + rehype-highlight/sanitize + highlight.js），
// lazy 成独立 chunk：首屏（侧边栏）不必等它，显著加快冷启动。
const TextResponseBlock = lazy(() =>
  import('./TextResponseBlock').then((m) => ({ default: m.TextResponseBlock })),
)

function groupBlocks(blocks: AgentBlock[]) {
  const grouped: { block: AgentBlock; result?: AgentBlock }[] = []
  const paired = new Set<string>()
  for (let i = 0; i < blocks.length; i++) {
    if (paired.has(blocks[i].id)) continue
    if (blocks[i].kind === 'tool_call') {
      let result: AgentBlock | undefined
      // 向前看最多 6 个 block 寻找配对的 tool_result（容忍中间穿插的 thinking/text）；
      // 遇到下一个 tool_call 即停止（避免错配到后续调用的结果）
      for (let j = i + 1; j < Math.min(i + 6, blocks.length); j++) {
        if (blocks[j].kind === 'tool_result' && !paired.has(blocks[j].id)) {
          result = blocks[j]
          paired.add(result.id)
          break
        }
        if (blocks[j].kind === 'tool_call') break
      }
      grouped.push({ block: blocks[i], result })
    } else {
      grouped.push({ block: blocks[i] })
    }
  }
  return grouped
}

function extractText(blocks: AgentBlock[] | undefined): string {
  if (!blocks) return ''
  return blocks
    .filter((b) => b.kind === 'text_response')
    .map((b) => (b.kind === 'text_response' ? b.text : ''))
    .join('\n')
}

export function AgentResponse({ message }: { message: ChatMessage }) {
  const blocks = message.blocks ?? []
  const grouped = groupBlocks(blocks)
  const plainText = extractText(blocks)

  return (
    <div className="group flex gap-3.5 fade-in">
      <span className="w-[30px] h-[30px] rounded-full inline-flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: 'var(--brand)', color: 'var(--ivory)' }}>
        <Sparkle size={16} weight="fill" />
      </span>
      <div className="flex-1 min-w-0">
        {blocks.length === 0 && <div className="typing-dots"><span /><span /><span /></div>}
        <div className="flex flex-col gap-2.5">
          {grouped.map(({ block, result }) => {
            switch (block.kind) {
              case 'thinking': return <ThinkingBlock key={block.id} block={block} />
              case 'tool_call': return <ToolCallBlock key={block.id} block={block} result={result} />
              // 孤儿 tool_result（未配对/乱序）：无需渲染 —— 配对的结果已通过 tool_call 的 result prop 显示
              case 'tool_result':
                return null
              case 'text_response': return (
                <Suspense key={block.id} fallback={null}>
                  <TextResponseBlock block={block} />
                </Suspense>
              )
              case 'error': return (
                <div key={block.id} className="text-sm px-3 py-2 rounded-lg" style={{ backgroundColor: 'var(--danger-bg)', color: 'var(--danger-text)', border: '1px solid var(--danger-border)' }}>
                  {block.text}
                </div>
              )
            }
          })}
        </div>
        {blocks.length > 0 && plainText && <MessageActions text={plainText} />}
      </div>
    </div>
  )
}
