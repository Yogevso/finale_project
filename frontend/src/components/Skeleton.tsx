type SkeletonProps = {
  className?: string
}

export default function Skeleton({ className = '' }: SkeletonProps) {
  return <span className={`block animate-pulse rounded-lg bg-slate-200/70 ${className}`} />
}
