import type { ReactNode } from 'react'
import { X } from '@phosphor-icons/react'
import { useChatStore } from '../../store'
import type { WsStatus } from '../../lib/wsClient'
import { ConfigSection } from './ConfigSection'
import { SystemPromptSection } from './SystemPromptSection'
import { ToolChainSection } from './ToolChainSection'

export function InspectorPanel() {
  const open = useChatStore((s) => s.inspectorOpen)
  const close = useChatStore((s) => s.closeInspector)
  const inspector = useChatStore((s) => s.inspector)
  const wsStatus = useChatStore((s) => s.wsStatus)

  if (!open) return null
  return (
    <aside className="flex flex-col h-full border-l"
      style={{ width: 360, borderColor: 'var(--border)', backgroundColor: 'var(--surface)' }}>
      <header className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--text)' }}>
          观测面板 <StatusBadge status={wsStatus} />
        </span>
        <button onClick={close} aria-label="关闭" style={{ color: 'var(--text-3)' }}><X size={18} /></button>
      </header>
      <div className="flex-1 overflow-auto p-4 space-y-5">
        <Section title="运行配置">
          <ConfigSection config={inspector.config} offline={wsStatus === 'disconnected'} />
        </Section>
        <Section title="System Prompt">
          <SystemPromptSection sp={inspector.systemPrompt} offline={wsStatus === 'disconnected'} />
        </Section>
        <Section title="工具调用链">
          <ToolChainSection toolCalls={inspector.toolCalls} />
        </Section>
      </div>
    </aside>
  )
}

function StatusBadge({ status }: { status: WsStatus }) {
  const map = {
    connected: { color: '#10b981', label: '已连接' },
    connecting: { color: '#f59e0b', label: '连接中' },
    disconnected: { color: '#9ca3af', label: '离线' },
  } as const
  const { color, label } = map[status]
  return (
    <span className="inline-flex items-center gap-1 text-xs font-normal" style={{ color: 'var(--text-3)' }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: color, display: 'inline-block' }} />
      {label}
    </span>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-3)' }}>{title}</h3>
      {children}
    </section>
  )
}
