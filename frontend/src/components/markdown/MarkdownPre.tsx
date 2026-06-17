import { useState, isValidElement, type ComponentPropsWithoutRef, type ReactElement, type ReactNode } from 'react'
import { Copy, Check } from '@phosphor-icons/react'
import 'highlight.js/styles/atom-one-dark.css'

export function MarkdownPre({ children, ...rest }: ComponentPropsWithoutRef<'pre'>) {
  const [copied, setCopied] = useState(false)
  const lang = extractLanguage(children)

  async function handleCopy() {
    const code = extractText(children)
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="rounded-lg my-3.5 overflow-hidden" style={{ backgroundColor: 'var(--code-bg)' }}>
      <div className="flex items-center justify-between px-3.5 py-2" style={{ borderBottom: '1px solid rgba(255,255,255,.06)', backgroundColor: 'rgba(255,255,255,.04)' }}>
        <span className="text-xs uppercase tracking-wide" style={{ fontFamily: 'var(--font-mono)', color: '#b0aea5' }}>{lang ?? 'text'}</span>
        <button onClick={handleCopy} className="inline-flex items-center gap-1.5 text-xs px-1.5 py-0.5 rounded transition-colors hover:bg-white/10" style={{ color: copied ? '#7fb38a' : '#b0aea5' }} aria-label="复制代码">
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? '已复制' : '复制'}
        </button>
      </div>
      <pre {...rest} className="px-4 py-3.5 overflow-x-auto text-[13px] leading-relaxed" style={{ color: '#e3e1d8' }}>{children}</pre>
    </div>
  )
}

type PreChild = { className?: string; children?: ReactNode }
function isPreChild(node: ReactNode): node is ReactElement<PreChild> { return isValidElement(node) }
function extractLanguage(children: ReactNode): string | null {
  if (isPreChild(children)) {
    const match = (children.props.className ?? '').match(/language-(\w+)/)
    return match ? match[1] : null
  }
  return null
}
function extractText(children: ReactNode): string {
  if (typeof children === 'string') return children
  if (Array.isArray(children)) return children.map(extractText).join('')
  if (isPreChild(children)) return extractText(children.props.children)
  return ''
}
