import { ChatHeader } from './ChatHeader'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { SessionSidebar } from './SessionSidebar'
import { useChatStore } from '../store'

export function ChatLayout() {
  const errorToast = useChatStore((s) => s.errorToast)
  const clearError = useChatStore((s) => s.clearError)

  return (
    <div className="flex h-full">
      <SessionSidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <ChatHeader />
        <MessageList />
        <ChatInput />
      </div>
      {errorToast && (
        <div
          className="fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm"
          style={{
            backgroundColor: 'var(--danger-bg)',
            color: 'var(--danger-text)',
            border: '1px solid var(--danger-border)',
          }}
          role="alert"
        >
          <div className="flex items-center justify-between gap-3">
            <span>{errorToast}</span>
            <button
              onClick={clearError}
              className="text-xs opacity-60 hover:opacity-100"
              aria-label="关闭"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
