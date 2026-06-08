import { useChatStore } from '../store'
import { useAutoScroll } from '../hooks/useAutoScroll'
import { UserBubble } from './UserBubble'
import { AgentResponse } from './AgentResponse'
import { SystemNotification } from './SystemNotification'

function MessageSkeleton() {
  return (
    <div className="flex gap-3 px-4 py-3">
      <div className="flex-1 space-y-2">
        <div className="h-4 rounded shimmer" style={{ width: '80%', backgroundColor: 'var(--surface-sand)' }} />
        <div className="h-4 rounded shimmer" style={{ width: '60%', backgroundColor: 'var(--surface-sand)' }} />
        <div className="h-4 rounded shimmer" style={{ width: '40%', backgroundColor: 'var(--surface-sand)' }} />
      </div>
    </div>
  )
}

export function MessageList() {
  const messages = useChatStore((s) => s.messages)
  const streamingMessage = useChatStore((s) => s.streamingMessage)
  const switchingSession = useChatStore((s) => s.switchingSession)
  const { containerRef, onScroll } = useAutoScroll<HTMLDivElement>(messages)

  if (switchingSession) {
    return (
      <div className="flex-1 overflow-y-auto px-4 py-4" style={{ backgroundColor: 'var(--bg-parchment)' }}>
        <div className="max-w-3xl mx-auto flex flex-col gap-4">
          <MessageSkeleton />
          <MessageSkeleton />
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef}
      onScroll={onScroll}
      className="flex-1 overflow-y-auto px-4 py-4"
      style={{ backgroundColor: 'var(--bg-parchment)' }}>
      <div className="max-w-3xl mx-auto flex flex-col gap-4">
        {messages.map((msg) => {
          if (msg.role === 'user') {
            return <UserBubble key={msg.id} message={msg} />
          }
          if (msg.role === 'agent') {
            return <AgentResponse key={msg.id} message={msg} />
          }
          if (msg.role === 'system') {
            return <SystemNotification key={msg.id} message={msg} />
          }
          return null
        })}
        {streamingMessage && <AgentResponse key={streamingMessage.id} message={streamingMessage} />}
      </div>
    </div>
  )
}
