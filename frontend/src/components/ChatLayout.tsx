import { ChatHeader } from './header/ChatHeader'
import { MessageList } from './message/MessageList'
import { ChatInput } from './composer/ChatInput'
import { SessionSidebar } from './sidebar/SessionSidebar'
import { InspectorPanel } from './inspector/InspectorPanel'
import { ComingSoon } from './ComingSoon'
import { AgentPanel } from './agent/AgentPanel'
import { useChatStore } from '../store'

export function ChatLayout() {
  const errorToast = useChatStore((s) => s.errorToast)
  const clearError = useChatStore((s) => s.clearError)
  const activeView = useChatStore((s) => s.activeView)

  return (
    <div className="flex h-full">
      {activeView === 'chat' && <SessionSidebar />}
      <div className="flex flex-col flex-1 min-w-0">
        <ChatHeader />
        {activeView === 'chat' ? (
          <>
            <MessageList />
            <ChatInput />
          </>
        ) : activeView === 'agent' ? (
          <AgentPanel />
        ) : (
          <ComingSoon name={activeView} />
        )}
      </div>
      <InspectorPanel />
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
