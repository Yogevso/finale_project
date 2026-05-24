import { Loader2 } from 'lucide-react'

interface LoadingOverlayProps {
  label?: string
  fullscreen?: boolean
  className?: string
}

export function LoadingOverlay({
  label = 'Loading...',
  fullscreen = false,
  className = '',
}: LoadingOverlayProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className={[
        fullscreen ? 'fixed inset-0 z-50' : 'absolute inset-0 z-20',
        'flex items-center justify-center bg-white/75 backdrop-blur-sm dark:bg-slate-950/75',
        className,
      ].filter(Boolean).join(' ')}
    >
      <span className="sr-only">{label}</span>
      <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-white px-4 py-3 shadow-lg dark:border-slate-800 dark:bg-slate-900">
        <Loader2 className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400" aria-hidden="true" />
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span>
      </div>
    </div>
  )
}
