interface ListSkeletonProps {
  rows?: number
  className?: string
}

export function ListSkeleton({
  rows = 5,
  className = '',
}: ListSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['space-y-3', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white/90 p-4 dark:border-slate-800 dark:bg-slate-900/80"
        >
          <div className="h-10 w-10 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-1/3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
            <div className="h-3 w-5/6 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          </div>
        </div>
      ))}
    </div>
  )
}
