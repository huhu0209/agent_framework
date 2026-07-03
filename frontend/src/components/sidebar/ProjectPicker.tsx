import { useEffect, useState } from 'react'
import { ArrowUp } from '@phosphor-icons/react'
import { API_BASE, authHeaders } from '../../store'

type Dir = { name: string; path: string }

// 返回父目录路径;home 起点(~)或根目录(/)无父级,返回 null
function parentDir(p: string): string | null {
  if (!p || p === '~' || p === '/') return null
  const idx = p.lastIndexOf('/')
  if (idx === 0) return '/'
  if (idx < 0) return null
  return p.slice(0, idx)
}

export function ProjectPicker({
  rootPath,
  onPick,
  onClose,
}: {
  rootPath: string
  onPick: (absPath: string) => void
  onClose: () => void
}) {
  const [cwd, setCwd] = useState(rootPath)
  const [dirs, setDirs] = useState<Dir[]>([])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/fs/list?path=${encodeURIComponent(cwd)}`, { headers: authHeaders() })
        if (!cancelled && res.ok) setDirs(await res.json())
      } catch { /* 静默 */ }
    })()
    return () => { cancelled = true }
  }, [cwd])

  const parent = parentDir(cwd)

  return (
    <div className="fixed inset-0 z-50 grid place-items-center" style={{ background: 'rgba(0,0,0,0.3)' }}>
      <div
        className="w-[480px] max-h-[70vh] overflow-auto rounded-xl p-4"
        style={{ background: 'var(--surface)', border: '1px solid var(--border-warm)' }}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <button
              onClick={() => parent && setCwd(parent)}
              disabled={!parent}
              className="inline-flex items-center justify-center w-7 h-7 rounded-md transition-colors hover:bg-[var(--sand)] disabled:opacity-30"
              style={{ color: 'var(--sb-muted)' }}
              aria-label="返回上一级"
              title="返回上一级"
            >
              <ArrowUp size={16} />
            </button>
            <span className="text-sm truncate" style={{ color: 'var(--sb-muted)' }}>{cwd}</span>
          </div>
          <button onClick={onClose} className="text-xs" style={{ color: 'var(--brand)' }}>取消</button>
        </div>
        <div className="space-y-0.5">
          {dirs.map((d) => (
            <button
              key={d.path}
              onClick={() => setCwd(d.path)}
              onDoubleClick={() => onPick(d.path)}
              className="block w-full text-left px-3 py-2 rounded-md text-sm hover:bg-[var(--sand)]"
              style={{ color: 'var(--sb-text)' }}
            >
              <span aria-hidden>📁</span>{' '}
              <span>{d.name}</span>
            </button>
          ))}
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={() => onPick(cwd)}
            className="px-4 py-1.5 rounded-md text-sm font-medium"
            style={{ background: 'var(--brand)', color: 'var(--ivory)' }}
          >
            选择
          </button>
        </div>
      </div>
    </div>
  )
}
