import { MagnifyingGlass } from '@phosphor-icons/react'
import { useChatStore } from '../../store'

export function SearchInput() {
  const searchQuery = useChatStore((s) => s.searchQuery)
  const setSearchQuery = useChatStore((s) => s.setSearchQuery)
  return (
    <div className="relative mx-3 mb-2">
      <MagnifyingGlass
        size={15}
        className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
        style={{ color: 'var(--sb-muted)' }}
      />
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="搜索对话"
        aria-label="搜索对话"
        className="w-full py-2 pl-9 pr-3 rounded-lg text-[13.5px] outline-none transition-colors"
        style={{
          backgroundColor: 'var(--sb-hover)',
          border: '1px solid transparent',
          color: 'var(--sb-text)',
        }}
        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--ring)')}
        onBlur={(e) => (e.currentTarget.style.borderColor = 'transparent')}
      />
    </div>
  )
}
