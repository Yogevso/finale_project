interface CardSkeletonProps {
  count?: number
  className?: string
}

export function CardSkeleton({
  count = 6,
  className = '',
}: CardSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['grid gap-4 sm:grid-cols-2 xl:grid-cols-3', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="h-4 w-2/3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="mt-3 h-3 w-1/4 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="mt-4 space-y-2">
            <div className="h-3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
            <div className="h-3 w-11/12 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
            <div className="h-3 w-3/4 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          </div>
          <div className="mt-5 h-8 w-28 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
        </div>
      ))}
    </div>
  )
}
