import type { ComponentPropsWithoutRef } from 'react'

export function MarkdownTable({ children, ...rest }: ComponentPropsWithoutRef<'table'>) {
  return (
    <div style={{ overflowX: 'auto', marginTop: '1em', marginBottom: '1em' }}>
      <table
        {...rest}
        className="markdown-table"
        style={{
          borderCollapse: 'collapse',
          width: '100%',
          fontSize: '0.875rem',
          lineHeight: '1.5',
          borderRadius: '8px',
          overflow: 'hidden',
        }}
      >
        {children}
      </table>
    </div>
  )
}
