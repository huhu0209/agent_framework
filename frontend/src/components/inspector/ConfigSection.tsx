import type { ConfigPayload } from '../../types'

export function ConfigSection({ config }: { config: ConfigPayload | null }) {
  if (!config) return <div className="text-sm" style={{ color: 'var(--text-3)' }}>等待 config…</div>
  return (
    <div className="space-y-2 text-sm">
      <Row label="模型" value={config.model} />
      <Row label="max_steps" value={String(config.max_steps)} />
      <Row label="profile" value={config.profile ?? '—'} />
      <Row label="permission" value={config.permission_mode ?? '—'} />
      <div>
        <div className="text-xs mb-1" style={{ color: 'var(--text-3)' }}>工具（{config.tools.length}）</div>
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
      <span style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="font-mono" style={{ color: 'var(--text)' }}>{value}</span>
    </div>
  )
}
