import { Inbox } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
  tone?: 'empty' | 'info' | 'success' | 'warning'
  size?: 'default' | 'compact'
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
  tone = 'empty',
  size = 'default',
}: EmptyStateProps) {
  const compact = size === 'compact'

  return (
    <div
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
        {icon ?? <Inbox className="h-8 w-8" aria-hidden="true" />}
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
      {description ? (
        <p
          className={[
            'state-copy',
            `state-copy--${tone}`,
            compact ? 'state-copy--compact' : '',
          ]
            .filter(Boolean)
            .join(' ')}
        >
          {description}
        </p>
      ) : null}
      {action ? (
        <div className={['state-actions', compact ? 'state-actions--compact' : ''].filter(Boolean).join(' ')}>
          <button type="button" onClick={action.onClick} className="btn-primary">
            {action.label}
          </button>
        </div>
      ) : null}
    </div>
  )
}
