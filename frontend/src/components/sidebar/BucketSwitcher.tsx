import { useEffect } from 'react'
import { useChatStore } from '../../store'

export function BucketSwitcher() {
  const buckets = useChatStore((s) => s.buckets)
  const currentBucket = useChatStore((s) => s.currentBucket)
  const setCurrentBucket = useChatStore((s) => s.setCurrentBucket)
  const loadBuckets = useChatStore((s) => s.loadBuckets)

  useEffect(() => { void loadBuckets() }, [loadBuckets])

  return (
    <div className="px-3 pt-2.5 pb-2.5">
      <select
        value={currentBucket}
        onChange={(e) => setCurrentBucket(e.target.value, null)}
        className="w-full px-2.5 py-1.5 rounded-md text-[13px]"
        style={{
          border: '1px solid var(--sb-border)',
          backgroundColor: 'var(--sb-bg)',
          color: 'var(--sb-text)',
        }}
        aria-label="切换项目桶"
      >
        {buckets.map((b) => (
          <option key={b.bucket} value={b.bucket}>{b.display_name}</option>
        ))}
      </select>
    </div>
  )
}
