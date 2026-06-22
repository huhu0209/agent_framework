import type { UsageState } from '../../types'

const WARN_THRESHOLD = 0.8

function formatNum(n: number): string {
  return n.toLocaleString('en-US')
}

export function UsageSection({ usage, offline }: { usage: UsageState | null; offline?: boolean }) {
  if (offline && !usage) {
    return <div className="text-sm" style={{ color: 'var(--text-3)' }}>观测面板离线，实时数据暂停。</div>
  }
  if (!usage) {
    return <div className="text-sm" style={{ color: 'var(--text-3)' }}>等待首次调用…</div>
  }

  const ratio = usage.max_context > 0 ? usage.input / usage.max_context : 0
  const pct = Math.min(ratio, 1)
  const warn = ratio >= WARN_THRESHOLD

  return (
    <div className="space-y-3 text-sm">
      <div>
        <div className="flex justify-between text-[11px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-3)' }}>
          <span>当前 / 上限</span>
          <span className="font-mono">{formatNum(usage.input)} / {formatNum(usage.max_context)}</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--surface)' }}>
          <div
            data-testid="usage-bar"
            data-warn={warn ? '1' : '0'}
            className="h-full rounded-full transition-all"
            style={{ width: `${pct * 100}%`, backgroundColor: warn ? 'var(--coral)' : 'var(--brand)' }}
          />
        </div>
        <div className="text-[11px] mt-1 font-mono" style={{ color: 'var(--text-3)' }}>{(ratio * 100).toFixed(2)}%</div>
      </div>
      <div className="space-y-1.5 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
        <UsageRow label="本次" input={usage.input} output={usage.output} />
        <UsageRow label="累计" input={usage.cumulative_input} output={usage.cumulative_output} />
      </div>
    </div>
  )
}

function UsageRow({ label, input, output }: { label: string; input: number; output: number }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="font-mono text-[13px]" style={{ color: 'var(--text-3)' }}>{label}</span>
      <span className="font-mono text-[13px]" style={{ color: 'var(--text)' }}>
        ↑ {formatNum(input)}{'　'}↓ {formatNum(output)}
      </span>
    </div>
  )
}
