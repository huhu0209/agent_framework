import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react'
import { ArrowUp, Plus, Microphone } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function ChatInput() {
  const [value, setValue] = useState('')
  const isStreaming = useChatStore((s) => s.isStreaming)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const composerDraft = useChatStore((s) => s.composerDraft)
  const setComposerDraft = useChatStore((s) => s.setComposerDraft)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const canSend = value.trim().length > 0 && !isStreaming

  useEffect(() => {
    if (composerDraft) {
      setValue(composerDraft)
      setComposerDraft('')
      requestAnimationFrame(() => textareaRef.current?.focus())
    }
  }, [composerDraft, setComposerDraft])

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [])

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
    <div className="px-6 pb-4 pt-2" style={{ backgroundColor: 'var(--bg)' }}>
      <div
        className="flex items-end gap-2 max-w-[760px] mx-auto px-4 py-2 rounded-[22px] transition-colors border border-[var(--border-2)] focus-within:border-[var(--ring)]"
        style={{ backgroundColor: 'var(--surface)' }}
      >
        {/* 流式期间不锁定输入框：允许用户预先输入下一条（发送由 canSend 守卫拦截） */}
        <textarea
          ref={textareaRef}
          className="flex-1 resize-none outline-none text-[15px] leading-relaxed"
          style={{ backgroundColor: 'transparent', color: 'var(--text)', maxHeight: 200, padding: '7px 0' }}
          rows={1}
          placeholder="给助手发消息"
          value={value}
          onChange={(e) => { setValue(e.target.value); adjustHeight() }}
          onKeyDown={handleKeyDown}
        />
        <button
          aria-label="添加"
          title="添加"
          className="shrink-0 w-9 h-9 inline-flex items-center justify-center rounded-full transition-colors hover:bg-[var(--sand)]"
          style={{ color: 'var(--text-2)' }}
        >
          <Plus size={18} />
        </button>
        <button
          aria-label="语音输入"
          title="语音输入"
          className="shrink-0 w-9 h-9 inline-flex items-center justify-center rounded-full transition-colors hover:bg-[var(--sand)]"
          style={{ color: 'var(--text-2)' }}
        >
          <Microphone size={18} />
        </button>
        <button
          onClick={handleSend}
          disabled={!canSend}
          aria-label="发送"
          className="shrink-0 w-9 h-9 inline-flex items-center justify-center rounded-full transition-transform active:scale-95"
          style={{
            backgroundColor: canSend ? 'var(--brand)' : 'var(--border-2)',
            color: canSend ? 'var(--ivory)' : 'var(--text-3)',
            cursor: canSend ? 'pointer' : 'not-allowed',
          }}
        >
          <ArrowUp size={18} />
        </button>
      </div>
      <p className="text-center text-[11.5px] mt-2 max-w-[760px] mx-auto" style={{ color: 'var(--text-3)' }}>
        助手可能出错，请核实重要的技术信息。
      </p>
    </div>
  )
}
