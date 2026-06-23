export function ComingSoon({ name }: { name: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-2">
      <div className="text-xl font-semibold capitalize" style={{ color: 'var(--text-2)' }}>{name}</div>
      <div className="text-sm" style={{ color: 'var(--text-3)' }}>开发中，敬请期待</div>
    </div>
  )
}
