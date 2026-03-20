type SkeletonProps = {
  className?: string
  label?: string
}

export default function Skeleton({ className = '', label = 'Loading' }: SkeletonProps) {
  return <span className={`block animate-pulse rounded-lg bg-slate-200/70 ${className}`} role="status" aria-label={label} />
}
