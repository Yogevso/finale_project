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
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div
      className={['rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 p-10 text-center dark:border-slate-700 dark:bg-slate-900/70', className].filter(Boolean).join(' ')}
    >
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-white text-slate-500 shadow-sm dark:bg-slate-950 dark:text-slate-300">
        {icon ?? <Inbox className="h-8 w-8" aria-hidden="true" />}
      </div>
      <h2 className="mt-4 text-xl font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
      {description ? (
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-600 dark:text-slate-400">{description}</p>
      ) : null}
      {action ? (
        <div className="mt-6 flex justify-center">
          <button type="button" onClick={action.onClick} className="btn-primary">
            {action.label}
          </button>
        </div>
      ) : null}
    </div>
  )
}
