import { useEffect } from 'react'
import { ChatLayout } from './components/ChatLayout'
import { useChatStore } from './store'

export default function App() {
  const addSystemMessage = useChatStore((s) => s.addSystemMessage)

  useEffect(() => {
    addSystemMessage('Session started. 输入消息开始对话。')
  }, [addSystemMessage])

  return <ChatLayout />
}
