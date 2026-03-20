type ChartSkeletonVariant = 'bar' | 'line' | 'pie'

interface ChartSkeletonProps {
  variant?: ChartSkeletonVariant
  height?: number
  className?: string
}

export function ChartSkeleton({
  variant = 'bar',
  height = 280,
  className = '',
}: ChartSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      <div className="h-4 w-40 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
      <div className="mt-6" style={{ height }}>
        {variant === 'pie' ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-40 w-40 animate-pulse rounded-full border-[18px] border-slate-200 border-t-slate-300 dark:border-slate-700 dark:border-t-slate-600" />
          </div>
        ) : variant === 'line' ? (
          <div className="flex h-full items-end gap-3">
            {Array.from({ length: 7 }).map((_, index) => (
              <div
                key={index}
                className="flex-1 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700"
                style={{ height: `${40 + ((index % 4) + 1) * 14}%` }}
              />
            ))}
          </div>
        ) : (
          <div className="flex h-full items-end gap-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div
                key={index}
                className="flex-1 animate-pulse rounded-t-2xl bg-slate-200 dark:bg-slate-700"
                style={{ height: `${28 + ((index % 5) + 1) * 11}%` }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
