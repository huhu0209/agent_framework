import { useCallback, useEffect, useRef } from 'react'

export function useAutoScroll<T extends HTMLElement>(dependency: unknown) {
  const containerRef = useRef<T>(null)
  const wasAtBottom = useRef(true)

  const checkBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    wasAtBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50
  }, [])

  useEffect(() => {
    if (wasAtBottom.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [dependency])

  return { containerRef, onScroll: checkBottom }
}
