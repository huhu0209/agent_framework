import { GearSix } from '@phosphor-icons/react'

export function UserArea() {
  return (
    <div className="p-2" style={{ borderTop: '1px solid var(--sb-border)' }}>
      <button
        className="flex items-center gap-2.5 w-full px-2 py-2 rounded-lg transition-colors hover:bg-[var(--sb-hover)]"
        style={{ color: 'var(--sb-text)' }}
        aria-label="设置"
        title="设置"
      >
        <span
          className="w-7 h-7 rounded-full inline-flex items-center justify-center text-[13px] font-semibold shrink-0"
          style={{ backgroundColor: 'var(--brand)', color: 'var(--ivory)' }}
        >
          小
        </span>
        <span className="flex-1 text-left leading-tight min-w-0">
          <span className="block text-[13.5px] font-medium">xiaohu</span>
          <span className="block text-[11.5px]" style={{ color: 'var(--sb-muted)' }}>本地部署 · GLM</span>
        </span>
        <GearSix size={17} style={{ color: 'var(--sb-muted)' }} />
      </button>
    </div>
  )
}
