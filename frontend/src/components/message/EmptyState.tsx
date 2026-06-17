import { Sparkle } from '@phosphor-icons/react'
import { SuggestCards } from './SuggestCards'

export function EmptyState() {
  return (
    <div className="flex-1 overflow-y-auto flex flex-col items-center px-6 pt-[12vh] pb-10 text-center" style={{ backgroundColor: 'var(--bg)' }}>
      <span className="w-14 h-14 rounded-2xl inline-flex items-center justify-center mb-5" style={{ backgroundColor: 'var(--brand)', color: 'var(--ivory)', boxShadow: '0 6px 20px rgba(201,100,66,.28)' }}>
        <Sparkle size={26} weight="fill" />
      </span>
      <h1 className="mb-3" style={{ fontFamily: 'var(--font-serif)', fontSize: 38, fontWeight: 500, lineHeight: 1.2, color: 'var(--text)' }}>
        今天想探索什么？
      </h1>
      <p className="mb-8 max-w-[460px]" style={{ fontSize: 15.5, lineHeight: 1.6, color: 'var(--text-2)' }}>
        这是一个基于 Orchestrator 模式的 Agent 系统。可以问问框架的 LLM Adapter、Tool System，或者编排流程是怎么运转的。
      </p>
      <SuggestCards />
    </div>
  )
}
