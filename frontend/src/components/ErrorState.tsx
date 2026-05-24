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
  tone?: 'error' | 'warning' | 'info'
  size?: 'default' | 'compact'
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'We could not load this content. Please try again.',
  onRetry,
  icon,
  className = '',
  retryLabel,
  retryLoading = false,
  tone = 'error',
  size = 'default',
}: ErrorStateProps) {
  const compact = size === 'compact'

  return (
    <div
      role="alert"
      className={[
        'state-card',
        `state-card--${tone}`,
        compact ? 'state-card--compact' : 'state-card--default',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div
        className={[
          'state-icon',
          `state-icon--${tone}`,
          compact ? 'state-icon--compact' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {icon ?? <AlertCircle className="h-7 w-7" aria-hidden="true" />}
      </div>
      <h2
        className={[
          'state-title',
          `state-title--${tone}`,
          compact ? 'state-title--compact' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {title}
      </h2>
      <p
        className={[
          'state-copy',
          `state-copy--${tone}`,
          compact ? 'state-copy--compact' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {message}
      </p>
      {onRetry ? (
        <div className={['state-actions', compact ? 'state-actions--compact' : ''].filter(Boolean).join(' ')}>
          <RetryButton loading={retryLoading} onClick={onRetry} label={retryLabel} />
        </div>
      ) : null}
    </div>
  )
}
