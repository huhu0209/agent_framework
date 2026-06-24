import { FolderOpen, Plus, SidebarSimple } from '@phosphor-icons/react'
import { useState } from 'react'
import { useChatStore } from '../../store'
import type { SessionInfo } from '../../types'
import { BucketSwitcher } from './BucketSwitcher'
import { ProjectPicker } from './ProjectPicker'
import { SearchInput } from './SearchInput'
import { SessionItem } from './SessionItem'
import { UserArea } from './UserArea'

const DAY_MS = 86400000

function groupSessions(sessions: SessionInfo[]): { label: string; items: SessionInfo[] }[] {
  const now = Date.now()
  const today: SessionInfo[] = [], yest: SessionInfo[] = [], week: SessionInfo[] = [], older: SessionInfo[] = []
  for (const s of sessions) {
    const ageMs = now - (s.created_at ?? 0) * 1000
    if (ageMs < DAY_MS) today.push(s)
    else if (ageMs < 2 * DAY_MS) yest.push(s)
    else if (ageMs < 7 * DAY_MS) week.push(s)
    else older.push(s)
  }
  return [
    { label: '今天', items: today },
    { label: '昨天', items: yest },
    { label: '前 7 天', items: week },
    { label: '更早', items: older },
  ].filter((g) => g.items.length > 0)
}

function SessionSkeleton() {
  const widths = ['75%', '60%', '80%', '55%', '70%']
  return (
    <div className="px-2 py-1 space-y-1">
      {widths.map((w, i) => (
        <div key={i} className="px-3 py-2.5">
          <div className="h-4 rounded shimmer" style={{ width: w, backgroundColor: 'var(--sand)' }} />
        </div>
      ))}
    </div>
  )
}

export function SessionSidebar() {
  const sessions = useChatStore((s) => s.sessions)
  const sessionId = useChatStore((s) => s.sessionId)
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)
  const searchQuery = useChatStore((s) => s.searchQuery)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)
  const renameSession = useChatStore((s) => s.renameSession)
  const newSession = useChatStore((s) => s.newSession)
  const toggleSidebar = useChatStore((s) => s.toggleSidebar)
  const sessionsLoading = useChatStore((s) => s.sessionsLoading)
  const prefetchSession = useChatStore((s) => s.prefetchSession)
  const ensureBucketFor = useChatStore((s) => s.ensureBucketFor)
  const [picking, setPicking] = useState(false)

  const q = searchQuery.trim().toLowerCase()
  const filtered = q ? sessions.filter((s) => s.title.toLowerCase().includes(q)) : sessions
  const groups = groupSessions(filtered)

  return (
    <aside
      className="flex flex-col h-full overflow-hidden"
      style={{
        width: '272px',
        minWidth: '272px',
        backgroundColor: 'var(--sb-bg)',
        borderRight: '1px solid var(--sb-border)',
        marginLeft: sidebarOpen ? 0 : -272,
        transition: 'margin-left .3s cubic-bezier(.4,0,.2,1)',
      }}
    >
      <BucketSwitcher />

      <div className="flex items-center gap-2 px-3 pt-3.5 pb-2.5">
        <button
          onClick={newSession}
          className="flex-1 flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors hover:bg-[var(--sb-hover)]"
          style={{ border: '1px solid var(--sb-border)', color: 'var(--sb-text)' }}
        >
          <Plus size={18} style={{ color: 'var(--brand)' }} />
          新对话
        </button>
        <button
          onClick={() => setPicking(true)}
          className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sb-hover)]"
          style={{ color: 'var(--sb-muted)' }}
          aria-label="添加项目"
          title="添加项目"
        >
          <FolderOpen size={20} />
        </button>
        <button
          onClick={toggleSidebar}
          className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sb-hover)]"
          style={{ color: 'var(--sb-muted)' }}
          aria-label="收起侧栏"
          title="收起侧栏"
        >
          <SidebarSimple size={20} />
        </button>
      </div>

      <SearchInput />

      <nav className="flex-1 overflow-y-auto px-2 pb-3">
        {sessionsLoading ? (
          <SessionSkeleton />
        ) : groups.length === 0 ? (
          <p className="text-center text-xs py-8" style={{ color: 'var(--sb-muted)' }}>
            {q ? '无匹配对话' : '暂无会话记录'}
          </p>
        ) : (
          groups.map((g) => (
            <div key={g.label} className="mb-3.5">
              <div className="text-[11px] font-medium px-2.5 py-1.5" style={{ color: 'var(--sb-muted)' }}>{g.label}</div>
              {g.items.map((s) => (
                <SessionItem
                  key={s.session_id}
                  session={s}
                  isActive={s.session_id === sessionId}
                  onSelect={() => switchSession(s.session_id)}
                  onDelete={() => deleteSession(s.session_id)}
                  onRename={(t) => renameSession(s.session_id, t)}
                  onHover={() => prefetchSession(s.session_id)}
                />
              ))}
            </div>
          ))
        )}
      </nav>

      <UserArea />

      {picking && (
        <ProjectPicker
          rootPath={navigator.platform.toLowerCase().includes('win') ? 'C:\\' : '/'}
          onPick={(abs) => { setPicking(false); void ensureBucketFor(abs) }}
          onClose={() => setPicking(false)}
        />
      )}
    </aside>
  )
}
