interface TableSkeletonProps {
  rows?: number
  columns?: number
  className?: string
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className = '',
}: TableSkeletonProps) {
  const templateColumns = `repeat(${columns}, minmax(0, 1fr))`

  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      <div
        className="grid gap-4 border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/60"
        style={{ gridTemplateColumns: templateColumns }}
      >
        {Array.from({ length: columns }).map((_, index) => (
          <div
            key={index}
            className="h-3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700"
          />
        ))}
      </div>
      <div className="divide-y divide-slate-200 dark:divide-slate-800">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div
            key={rowIndex}
            className="grid gap-4 px-4 py-4"
            style={{ gridTemplateColumns: templateColumns }}
          >
            {Array.from({ length: columns }).map((__, columnIndex) => (
              <div
                key={`${rowIndex}-${columnIndex}`}
                className={`h-3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700 ${
                  columnIndex === 0 ? 'w-3/4' : columnIndex === columns - 1 ? 'w-1/2' : 'w-full'
                }`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
