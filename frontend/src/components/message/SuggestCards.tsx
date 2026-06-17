import { useChatStore } from '../../store'

const SUGGESTIONS = [
  'LLM Adapter 支持哪些 provider？',
  'Tool 是如何注册和调用的？',
  'Orchestrator 编排模式怎么扩展？',
  'ReAct 循环的终止条件是什么？',
]

export function SuggestCards() {
  const setComposerDraft = useChatStore((s) => s.setComposerDraft)
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-[560px]">
      {SUGGESTIONS.map((s) => (
        <button
          key={s}
          onClick={() => setComposerDraft(s)}
          className="text-left px-4 py-3.5 rounded-xl text-sm leading-snug transition-colors"
          style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border-2)', color: 'var(--text)' }}
        >
          {s}
        </button>
      ))}
    </div>
  )
}
