import { useRef, useState, useEffect } from 'react'
import { ChatTeardrop, PencilSimple, Trash, Check, X } from '@phosphor-icons/react'
import type { SessionInfo } from '../../types'

interface Props {
  session: SessionInfo
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onRename: (title: string) => void
  onHover: () => void
}

export function SessionItem({ session, isActive, onSelect, onDelete, onRename, onHover }: Props) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(session.title)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const hoverRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => () => { if (hoverRef.current) clearTimeout(hoverRef.current) }, [])

  if (isEditing) {
    return (
      <div className="px-2 py-1.5">
        <input
          type="text"
          value={editTitle}
          autoFocus
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && editTitle.trim()) { onRename(editTitle.trim()); setIsEditing(false) }
            if (e.key === 'Escape') { setEditTitle(session.title); setIsEditing(false) }
          }}
          onBlur={() => {
            if (editTitle.trim() && editTitle.trim() !== session.title) onRename(editTitle.trim())
            setIsEditing(false)
          }}
          className="w-full px-2 py-1 text-sm rounded outline-none"
          style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border-2)', color: 'var(--text)' }}
        />
      </div>
    )
  }

  return (
    <div
      className="group relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-colors hover:bg-[var(--sb-hover)]"
      style={{ backgroundColor: isActive ? 'var(--sb-active)' : 'transparent' }}
      onClick={confirmDelete ? undefined : onSelect}
      onMouseEnter={() => { hoverRef.current = setTimeout(onHover, 200) }}
      onMouseLeave={() => { if (hoverRef.current) clearTimeout(hoverRef.current) }}
    >
      {isActive && (
        <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r" style={{ backgroundColor: 'var(--brand)' }} />
      )}
      <ChatTeardrop size={15} className="shrink-0" style={{ color: 'var(--sb-muted)' }} />
      {confirmDelete ? (
        <div className="flex items-center gap-1 text-xs flex-1" onClick={(e) => e.stopPropagation()}>
          <span style={{ color: 'var(--sb-muted)' }}>删除？</span>
          <button onClick={() => { onDelete(); setConfirmDelete(false) }} className="px-1.5 py-0.5 rounded inline-flex items-center" style={{ backgroundColor: 'var(--danger)', color: 'var(--ivory)' }} aria-label="确认删除"><Check size={12} /></button>
          <button onClick={() => setConfirmDelete(false)} className="px-1.5 py-0.5 rounded inline-flex items-center" style={{ backgroundColor: 'var(--sb-active)', color: 'var(--sb-text)' }} aria-label="取消"><X size={12} /></button>
        </div>
      ) : (
        <>
          <span className="flex-1 truncate text-[13.5px]" style={{ color: 'var(--sb-text)' }}>{session.title}</span>
          <div className="hidden group-hover:flex gap-0.5" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => { setEditTitle(session.title); setIsEditing(true) }} className="p-1 rounded hover:bg-[var(--sb-active)] inline-flex items-center" style={{ color: 'var(--sb-muted)' }} aria-label="重命名"><PencilSimple size={14} /></button>
            <button onClick={() => setConfirmDelete(true)} className="p-1 rounded hover:bg-[var(--sb-active)] inline-flex items-center" style={{ color: 'var(--sb-muted)' }} aria-label="删除"><Trash size={14} /></button>
          </div>
        </>
      )}
    </div>
  )
}
