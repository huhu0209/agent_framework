import { useEffect, useRef } from 'react'
import { ChatLayout } from './components/ChatLayout'
import { useChatStore } from './store'

export default function App() {
  const addSystemMessage = useChatStore((s) => s.addSystemMessage)
  const mounted = useRef(false)

  useEffect(() => {
    if (mounted.current) return
    mounted.current = true
    addSystemMessage('Session started. 输入消息开始对话。')
  }, [addSystemMessage])

  return <ChatLayout />
}
