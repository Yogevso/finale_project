interface StatCardSkeletonProps {
  count?: number
  className?: string
}

export function StatCardSkeleton({
  count = 4,
  className = '',
}: StatCardSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['grid gap-4 sm:grid-cols-2 xl:grid-cols-4', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-3">
              <div className="h-3 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
              <div className="h-8 w-20 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
            </div>
            <div className="h-12 w-12 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-700" />
          </div>
          <div className="mt-4 h-3 w-1/2 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
        </div>
      ))}
    </div>
  )
}
