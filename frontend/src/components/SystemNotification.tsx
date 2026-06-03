import type { ChatMessage } from '../types'

export function SystemNotification({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-center">
      <span className="text-sm px-4 py-1.5 rounded-full"
        style={{
          backgroundColor: 'rgba(232, 230, 220, 0.5)',
          color: 'var(--text-tertiary)',
        }}>
        {message.content}
      </span>
    </div>
  )
}
