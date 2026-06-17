import { useEffect, useRef } from 'react'
import { ChatLayout } from './components/ChatLayout'
import { useChatStore } from './store'
import { restoreCache, clearStaleEntries } from './lib/cache'

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

function readInitialTheme(): 'light' | 'dark' {
  try {
    const saved = localStorage.getItem('chat-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* ignore */ }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default function App() {
  const loadSessions = useChatStore((s) => s.loadSessions)
  const setTheme = useChatStore((s) => s.setTheme)
  const mounted = useRef(false)

  useEffect(() => {
    if (mounted.current) return
    mounted.current = true
    setTheme(readInitialTheme())

    // Restore persistent cache, then load sessions with preview
    restoreCache().then((cache) => {
      useChatStore.setState({ messageCache: cache })
      loadSessions()
    })
    clearStaleEntries(SEVEN_DAYS_MS)
  }, [loadSessions, setTheme])

  return <ChatLayout />
}
