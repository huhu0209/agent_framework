import type { ChatMessage } from '../../types'

export function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end fade-in">
      <div
        className="max-w-[78%] px-4 py-3 text-[15px] leading-relaxed"
        style={{ backgroundColor: 'var(--sand)', color: 'var(--text)', borderRadius: '18px 18px 4px 18px' }}
      >
        {message.content}
      </div>
    </div>
  )
}
