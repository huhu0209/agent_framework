import type { ReactNode } from 'react'
import { X, SlidersHorizontal, Quotes, TreeStructure, Gauge } from '@phosphor-icons/react'
import { useChatStore } from '../../store'
import type { WsStatus } from '../../lib/wsClient'
import { ConfigSection } from './ConfigSection'
import { SystemPromptSection } from './SystemPromptSection'
import { ToolChainSection } from './ToolChainSection'
import { UsageSection } from './UsageSection'

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
      <div className="flex-1 overflow-auto p-3.5 space-y-3">
        <Section title="运行配置" icon={<SlidersHorizontal size={13} />}>
          <ConfigSection config={inspector.config} offline={wsStatus === 'disconnected'} />
        </Section>
        <Section title="System Prompt" icon={<Quotes size={13} />}>
          <SystemPromptSection sp={inspector.systemPrompt} offline={wsStatus === 'disconnected'} />
        </Section>
        <Section title="用量" icon={<Gauge size={13} />}>
          <UsageSection usage={inspector.usage} offline={wsStatus === 'disconnected'} />
        </Section>
        <Section title="工具调用链" icon={<TreeStructure size={13} />}>
          <ToolChainSection toolCalls={inspector.toolCalls} />
        </Section>
      </div>
    </aside>
  )
}

function StatusBadge({ status }: { status: WsStatus }) {
  const map = {
    connected: { color: 'var(--success)', label: '已连接' },
    connecting: { color: 'var(--coral)', label: '连接中' },
    disconnected: { color: 'var(--text-3)', label: '离线' },
  } as const
  const { color, label } = map[status]
  return (
    <span className="inline-flex items-center gap-1 text-xs font-normal" style={{ color: 'var(--text-3)' }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: color, display: 'inline-block' }} />
      {label}
    </span>
  )
}

function Section({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section
      className="rounded-lg p-3.5"
      style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border)' }}
    >
      <h3 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider mb-3"
        style={{ color: 'var(--text-3)' }}>
        {icon}
        {title}
      </h3>
      {children}
    </section>
  )
}
