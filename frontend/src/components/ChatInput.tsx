import { useState, type KeyboardEvent } from 'react'
import { useChatStore } from '../store'

export function ChatInput() {
  const [value, setValue] = useState('')
  const isStreaming = useChatStore((s) => s.isStreaming)
  const sendMessage = useChatStore((s) => s.sendMessage)

  const canSend = value.trim().length > 0 && !isStreaming

  const handleSend = () => {
    if (!canSend) return
    sendMessage(value.trim())
    setValue('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="px-4 py-3"
      style={{ backgroundColor: 'var(--bg-ivory)', borderTop: '1px solid var(--border-cream)' }}>
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          className="flex-1 resize-none rounded-xl px-4 py-2.5 text-base outline-none"
          style={{
            backgroundColor: 'var(--bg-parchment)',
            border: '1px solid var(--border-cream)',
            color: 'var(--text-primary)',
            minHeight: '44px',
            maxHeight: '120px',
          }}
          rows={1}
          placeholder="输入消息…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
        />
        <button
          className="shrink-0 h-11 px-4 rounded-xl text-sm font-medium transition-opacity"
          style={{
            backgroundColor: canSend ? 'var(--accent-terracotta)' : 'var(--surface-sand)',
            color: canSend ? 'var(--bg-ivory)' : 'var(--text-tertiary)',
            cursor: canSend ? 'pointer' : 'not-allowed',
          }}
          onClick={handleSend}
          disabled={!canSend}>
          发送
        </button>
      </div>
    </div>
  )
}
