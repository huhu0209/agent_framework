import type { ChatMessage } from '../types'

export function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[75%] px-4 py-2.5 rounded-xl"
        style={{
          backgroundColor: 'rgba(201, 100, 66, 0.10)',
          color: 'var(--text-primary)',
        }}>
        {message.content}
      </div>
    </div>
  )
}
