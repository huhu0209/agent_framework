import { ChatHeader } from './ChatHeader'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { SessionSidebar } from './SessionSidebar'

export function ChatLayout() {
  return (
    <div className="flex h-full">
      <SessionSidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <ChatHeader />
        <MessageList />
        <ChatInput />
      </div>
    </div>
  )
}
