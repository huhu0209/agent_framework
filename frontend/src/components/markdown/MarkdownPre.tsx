import { useState, isValidElement, type ComponentPropsWithoutRef, type ReactElement, type ReactNode } from 'react'

export function MarkdownPre({ children, ...rest }: ComponentPropsWithoutRef<'pre'>) {
  const [copied, setCopied] = useState(false)
  const lang = extractLanguage(children)

  async function handleCopy() {
    const code = extractText(children)
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // H-FE1: 非 HTTPS/权限拒绝时 writeText reject，降级提示而非 unhandled rejection
      setCopied(false)
    }
  }

  return (
    <div style={{ position: 'relative', marginTop: '1em', marginBottom: '1em' }}>
      <pre
        {...rest}
        style={{
          backgroundColor: '#f6f8fa',
          borderRadius: '8px',
          padding: '1rem',
          overflowX: 'auto',
          fontSize: '0.875rem',
          lineHeight: '1.5',
        }}
      >
        {children}
      </pre>
      <div style={{ position: 'absolute', top: '0.5rem', right: '0.5rem', display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
        {lang && (
          <span
            className="lang-label"
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {lang}
          </span>
        )}
        <button
          onClick={handleCopy}
          title="Copy code"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: copied ? '#1a7f37' : 'var(--text-tertiary)',
            fontSize: '0.8rem',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  )
}

type PreChild = { className?: string; children?: ReactNode }

/** 类型守卫：收窄 ReactNode 为带 className/children 的 ReactElement，替代裸 as 断言 */
function isPreChild(node: ReactNode): node is ReactElement<PreChild> {
  return isValidElement(node)
}

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
  if (isPreChild(children)) {
    return extractText(children.props.children)
  }
  return ''
}
