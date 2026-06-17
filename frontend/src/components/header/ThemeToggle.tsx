import { Moon, Sun } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function ThemeToggle() {
  const theme = useChatStore((s) => s.theme)
  const toggleTheme = useChatStore((s) => s.toggleTheme)
  return (
    <button
      onClick={toggleTheme}
      className="inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors hover:bg-[var(--sand)]"
      style={{ color: 'var(--text-2)' }}
      aria-label="切换主题"
      title="切换主题"
    >
      {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  )
}
