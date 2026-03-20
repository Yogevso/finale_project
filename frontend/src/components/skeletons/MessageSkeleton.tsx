interface MessageSkeletonProps {
  rows?: number
  className?: string
}

export function MessageSkeleton({
  rows = 4,
  className = '',
}: MessageSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['space-y-4 px-4 py-5', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      {Array.from({ length: rows }).map((_, index) => {
        const isOwn = index % 2 === 1
        return (
          <div
            key={index}
            className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[72%] space-y-2 ${isOwn ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`h-3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700 ${
                  isOwn ? 'ml-auto w-24' : 'w-20'
                }`}
              />
              <div
                className={`rounded-3xl px-4 py-4 ${
                  isOwn
                    ? 'bg-sky-100 dark:bg-sky-950/50'
                    : 'bg-white dark:bg-slate-900'
                }`}
              >
                <div className="h-3 w-48 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
                <div className="mt-2 h-3 w-32 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
