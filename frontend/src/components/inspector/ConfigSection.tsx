import { Sparkle } from '@phosphor-icons/react'
import type { ConfigPayload } from '../../types'

export function ConfigSection({ config, offline }: { config: ConfigPayload | null; offline?: boolean }) {
  if (offline && !config) {
    return <div className="text-sm" style={{ color: 'var(--text-3)' }}>观测面板离线，实时数据暂停。</div>
  }
  if (!config) return <div className="text-sm" style={{ color: 'var(--text-3)' }}>等待 config…</div>
  return (
    <div className="space-y-3 text-sm">
      <div>
        <div className="text-[11px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-3)' }}>模型</div>
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[13px] font-medium font-mono"
          style={{ backgroundColor: 'var(--brand)', color: 'var(--ivory)' }}>
          <Sparkle size={12} weight="fill" />
          {config.model}
        </span>
      </div>
      <div className="space-y-1.5 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
        <Row label="max_steps" value={String(config.max_steps)} />
        <Row label="profile" value={config.profile ?? '—'} />
        <Row label="permission" value={config.permission_mode ?? '—'} />
      </div>
      <div className="pt-3" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="text-[11px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-3)' }}>工具（{config.tools.length}）</div>
        <div className="flex flex-wrap gap-1">
          {config.tools.map((t) => (
            <span key={t} className="px-1.5 py-0.5 rounded text-xs font-mono"
              style={{ backgroundColor: 'var(--sand)', color: 'var(--text-2)' }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="font-mono text-[13px]" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="font-mono text-[13px]" style={{ color: 'var(--text)' }}>{value}</span>
    </div>
  )
}
