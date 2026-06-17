import { useState } from 'react'
import { Copy, ArrowClockwise, Check } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function MessageActions({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const messages = useChatStore((s) => s.messages)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {
      setCopied(false)
    }
  }

  // 重新生成：重发上一条 user 消息。并发由 store.sendMessage 的 isStreaming 守卫拦截
  function handleRegenerate() {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    if (lastUser?.content) sendMessage(lastUser.content)
  }

  return (
    <div className="flex gap-1 mt-2.5 opacity-0 transition-opacity group-hover:opacity-100">
      <button onClick={handleCopy} className="inline-flex items-center justify-center w-7 h-7 rounded transition-colors hover:bg-[var(--sand)]" style={{ color: 'var(--text-3)' }} aria-label="复制" title="复制">
        {copied ? <Check size={15} /> : <Copy size={15} />}
      </button>
      <button onClick={handleRegenerate} className="inline-flex items-center justify-center w-7 h-7 rounded transition-colors hover:bg-[var(--sand)]" style={{ color: 'var(--text-3)' }} aria-label="重新生成" title="重新生成">
        <ArrowClockwise size={15} />
      </button>
    </div>
  )
}
