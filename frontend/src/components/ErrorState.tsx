import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { RetryButton } from './RetryButton'

interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  icon?: ReactNode
  className?: string
  retryLabel?: string
  retryLoading?: boolean
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'We could not load this content. Please try again.',
  onRetry,
  icon,
  className = '',
  retryLabel,
  retryLoading = false,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={['rounded-3xl border border-rose-200 bg-rose-50/90 p-8 text-center text-rose-900 dark:border-rose-900/70 dark:bg-rose-950/40 dark:text-rose-100', className].filter(Boolean).join(' ')}
    >
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-white/80 text-rose-600 shadow-sm dark:bg-rose-900/50 dark:text-rose-200">
        {icon ?? <AlertCircle className="h-7 w-7" aria-hidden="true" />}
      </div>
      <h2 className="mt-4 text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-rose-700 dark:text-rose-200/85">{message}</p>
      {onRetry ? (
        <div className="mt-6 flex justify-center">
          <RetryButton loading={retryLoading} onClick={onRetry} label={retryLabel} />
        </div>
      ) : null}
    </div>
  )
}
