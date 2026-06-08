import { useState, type ComponentPropsWithoutRef, type ReactNode } from 'react'

export function MarkdownPre({ children, ...rest }: ComponentPropsWithoutRef<'pre'>) {
  const [copied, setCopied] = useState(false)
  const lang = extractLanguage(children)

  async function handleCopy() {
    const code = extractText(children)
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
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
          {copied ? '✓' : 'Copy'}
        </button>
      </div>
    </div>
  )
}

function extractLanguage(children: ReactNode): string | null {
  if (children && typeof children === 'object' && 'props' in children) {
    const className = (children as { props?: { className?: string } }).props?.className ?? ''
    const match = className.match(/language-(\w+)/)
    return match ? match[1] : null
  }
  return null
}

function extractText(children: ReactNode): string {
  if (typeof children === 'string') return children
  if (Array.isArray(children)) return children.map(extractText).join('')
  if (children && typeof children === 'object' && 'props' in children) {
    return extractText((children as { props?: { children?: ReactNode } }).props?.children)
  }
  return ''
}
