interface FormSkeletonProps {
  fields?: number
  className?: string
}

export function FormSkeleton({
  fields = 4,
  className = '',
}: FormSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={['space-y-5 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900', className].filter(Boolean).join(' ')}
    >
      <span className="sr-only">Loading...</span>
      {Array.from({ length: fields }).map((_, index) => (
        <div key={index} className="space-y-2">
          <div className="h-3 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
          <div className="h-11 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />
        </div>
      ))}
      <div className="flex justify-end gap-3 pt-2">
        <div className="h-10 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
        <div className="h-10 w-32 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
      </div>
    </div>
  )
}
