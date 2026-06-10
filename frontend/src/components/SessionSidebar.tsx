import { useRef, useState, useEffect } from 'react'
import { useChatStore } from '../store'
import type { SessionInfo } from '../types'

function SessionSkeleton() {
  const widths = ['75%', '60%', '80%', '55%', '70%']
  return (
    <div className="px-2 py-1 space-y-1">
      {widths.map((w, i) => (
        <div key={i} className="px-3 py-2.5">
          <div
            className="h-4 rounded shimmer"
            style={{ width: w, backgroundColor: 'var(--surface-sand)' }}
          />
        </div>
      ))}
    </div>
  )
}

function SessionItem({
  session,
  isActive,
  onSelect,
  onDelete,
  onRename,
  onHover,
}: {
  session: SessionInfo
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onRename: (title: string) => void
  onHover: () => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(session.title)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const hoverRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    return () => {
      if (hoverRef.current) clearTimeout(hoverRef.current)
    }
  }, [])

  if (isEditing) {
    return (
      <div className="px-2 py-1.5">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && editTitle.trim()) {
              onRename(editTitle.trim())
              setIsEditing(false)
            }
            if (e.key === 'Escape') {
              setEditTitle(session.title)
              setIsEditing(false)
            }
          }}
          onBlur={() => {
            if (editTitle.trim() && editTitle.trim() !== session.title) {
              onRename(editTitle.trim())
            }
            setIsEditing(false)
          }}
          autoFocus
          className="w-full px-2 py-1 text-sm rounded"
          style={{
            backgroundColor: 'var(--bg-ivory)',
            border: '1px solid var(--border-warm)',
            color: 'var(--text-primary)',
            outline: 'none',
          }}
        />
      </div>
    )
  }

  return (
    <div
      className="group flex items-center gap-1 px-3 py-2 cursor-pointer rounded-r-lg transition-colors hover:bg-[var(--bg-ivory)]"
      style={{
        backgroundColor: isActive ? 'var(--bg-ivory)' : 'transparent',
        borderLeft: isActive ? '3px solid var(--accent-terracotta)' : '3px solid transparent',
      }}
      onClick={confirmDelete ? undefined : onSelect}
      onMouseEnter={() => {
        hoverRef.current = setTimeout(onHover, 200)
      }}
      onMouseLeave={() => {
        if (hoverRef.current) clearTimeout(hoverRef.current)
      }}
    >
      <div className="flex-1 min-w-0">
        {confirmDelete ? (
          <div className="flex items-center gap-2 text-xs">
            <span style={{ color: 'var(--text-secondary)' }}>删除？</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
                setConfirmDelete(false)
              }}
              className="px-2 py-0.5 rounded"
              style={{ backgroundColor: '#b53333', color: '#faf9f5' }}
            >
              确认
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setConfirmDelete(false)
              }}
              className="px-2 py-0.5 rounded"
              style={{ backgroundColor: 'var(--surface-sand)', color: 'var(--text-primary)' }}
            >
              取消
            </button>
          </div>
        ) : (
          <span
            className="block text-sm truncate"
            style={{
              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: isActive ? 500 : 400,
            }}
          >
            {session.title}
          </span>
        )}
      </div>
      {!confirmDelete && (
        <div
          className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => {
              setEditTitle(session.title)
              setIsEditing(true)
            }}
            className="p-1 rounded transition-colors text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
            aria-label="重命名"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" />
            </svg>
          </button>
          <button
            onClick={() => setConfirmDelete(true)}
            className="p-1 rounded transition-colors text-[var(--text-tertiary)] hover:text-[#b53333]"
            aria-label="删除"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <line x1="3" y1="4" x2="13" y2="4" />
              <line x1="5" y1="4" x2="5.5" y2="13" />
              <line x1="10.5" y1="4" x2="10" y2="13" />
              <path d="M5.5 1h5" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}

export function SessionSidebar() {
  const sessions = useChatStore((s) => s.sessions)
  const sessionId = useChatStore((s) => s.sessionId)
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)
  const renameSession = useChatStore((s) => s.renameSession)
  const newSession = useChatStore((s) => s.newSession)
  const sessionsLoading = useChatStore((s) => s.sessionsLoading)
  const prefetchSession = useChatStore((s) => s.prefetchSession)

  if (!sidebarOpen) return null

  return (
    <aside
      className="flex flex-col h-full overflow-hidden"
      style={{
        width: '280px',
        minWidth: '280px',
        backgroundColor: 'var(--bg-parchment)',
        borderRight: '1px solid var(--border-cream)',
      }}
    >
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={newSession}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-[var(--border-warm)]"
          style={{
            backgroundColor: 'var(--surface-sand)',
            color: 'var(--text-primary)',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <line x1="7" y1="2" x2="7" y2="12" />
            <line x1="2" y1="7" x2="12" y2="7" />
          </svg>
          新建会话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        {sessionsLoading ? (
          <SessionSkeleton />
        ) : (
          <>
            {sessions.map((session) => (
              <SessionItem
                key={session.session_id}
                session={session}
                isActive={session.session_id === sessionId}
                onSelect={() => switchSession(session.session_id)}
                onDelete={() => deleteSession(session.session_id)}
                onRename={(title) => renameSession(session.session_id, title)}
                onHover={() => prefetchSession(session.session_id)}
              />
            ))}
            {sessions.length === 0 && (
              <p
                className="text-center text-xs py-8"
                style={{ color: 'var(--text-tertiary)' }}
              >
                暂无会话记录
              </p>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
