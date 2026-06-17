import { useRef, useCallback, useState, useEffect } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useChatStore } from '../../store'
import { UserBubble } from './UserBubble'
import { AgentResponse } from './AgentResponse'
import { SystemNotification } from './SystemNotification'

function MessageSkeleton() {
  return (
    <div className="flex gap-3 px-4 py-3">
      <div className="flex-1 space-y-2">
        <div className="h-4 rounded shimmer" style={{ width: '80%', backgroundColor: 'var(--sand)' }} />
        <div className="h-4 rounded shimmer" style={{ width: '60%', backgroundColor: 'var(--sand)' }} />
        <div className="h-4 rounded shimmer" style={{ width: '40%', backgroundColor: 'var(--sand)' }} />
      </div>
    </div>
  )
}

export function MessageList() {
  const messages = useChatStore((s) => s.messages)
  const streamingMessage = useChatStore((s) => s.streamingMessage)
  const switchingSession = useChatStore((s) => s.switchingSession)
  const hasMore = useChatStore((s) => s.hasMore)
  const loadingOlder = useChatStore((s) => s.loadingOlder)
  const loadOlderMessages = useChatStore((s) => s.loadOlderMessages)
  const loadingFullHistory = useChatStore((s) => s.loadingFullHistory)

  const parentRef = useRef<HTMLDivElement>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)

  const allItems = [...messages, ...(streamingMessage ? [streamingMessage] : [])]

  const virtualizer = useVirtualizer({
    count: allItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
    overscan: 5,
    getItemKey: (i) => allItems[i].id,
  })

  const handleScroll = useCallback(() => {
    const el = parentRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setIsAtBottom(distanceFromBottom < 100)
    if (el.scrollTop < 100 && hasMore && !loadingOlder) loadOlderMessages()
  }, [hasMore, loadingOlder, loadOlderMessages])

  useEffect(() => {
    if (!isAtBottom) return
    const count = allItems.length
    if (count === 0) return
    virtualizer.scrollToIndex(count - 1, { align: 'end' })
  }, [allItems.length, isAtBottom, virtualizer])

  useEffect(() => {
    if (switchingSession) return
    requestAnimationFrame(() => {
      if (allItems.length > 0) virtualizer.scrollToIndex(allItems.length - 1, { align: 'end' })
    })
  }, [switchingSession])

  if (switchingSession) {
    return (
      <div className="flex-1 overflow-y-auto px-6 py-8" style={{ backgroundColor: 'var(--bg)' }}>
        <div className="max-w-[760px] mx-auto flex flex-col gap-4">
          <MessageSkeleton />
          <MessageSkeleton />
        </div>
      </div>
    )
  }

  return (
    <div ref={parentRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-6 py-8" style={{ backgroundColor: 'var(--bg)' }}>
      {loadingOlder && <div className="text-center text-xs py-2" style={{ color: 'var(--text-3)' }}>加载更多...</div>}
      {loadingFullHistory && <div className="text-center text-xs py-2" style={{ color: 'var(--text-3)' }}>加载完整历史...</div>}
      <div className="max-w-[760px] mx-auto" style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const msg = allItems[virtualItem.index]
          return (
            <div key={virtualItem.key} data-testid="message-item" style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${virtualItem.start}px)` }}>
              {msg.role === 'user' && <UserBubble message={msg} />}
              {msg.role === 'agent' && <AgentResponse message={msg} />}
              {msg.role === 'system' && <SystemNotification message={msg} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
