import type { ComponentPropsWithoutRef } from 'react'

export function MarkdownAnchor({ children, href, ...rest }: ComponentPropsWithoutRef<'a'>) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{ color: 'var(--coral)', textDecoration: 'none' }}
      className="hover:underline inline-flex items-center gap-0.5"
      {...rest}
    >
      {children}
      <svg
        width="12"
        height="12"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ marginLeft: '2px', flexShrink: 0 }}
        aria-hidden="true"
      >
        <path d="M6 3H13V10" />
        <path d="M13 3L6 10" />
      </svg>
    </a>
  )
}
