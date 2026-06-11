import { useEffect, useRef } from 'react'
import { ChatLayout } from './components/ChatLayout'
import { useChatStore } from './store'
import { restoreCache, clearStaleEntries } from './lib/cache'

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

export default function App() {
  const addSystemMessage = useChatStore((s) => s.addSystemMessage)
  const loadSessions = useChatStore((s) => s.loadSessions)
  const mounted = useRef(false)

  useEffect(() => {
    if (mounted.current) return
    mounted.current = true
    addSystemMessage('Session started. 输入消息开始对话。')

    // Restore persistent cache, then load sessions with preview
    restoreCache().then((cache) => {
      useChatStore.setState({ messageCache: cache })
      loadSessions()
    })
    clearStaleEntries(SEVEN_DAYS_MS)
  }, [addSystemMessage, loadSessions])

  return <ChatLayout />
}
