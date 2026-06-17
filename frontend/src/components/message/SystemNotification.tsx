import type { ChatMessage } from '../../types'

export function SystemNotification({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-center">
      <span className="text-sm px-4 py-1.5 rounded-full" style={{ backgroundColor: 'var(--sand)', color: 'var(--text-3)' }}>{message.content}</span>
    </div>
  )
}
