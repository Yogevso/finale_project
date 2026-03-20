import { Loader2, RotateCw } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'

interface RetryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean
  label?: string
}

export function RetryButton({
  loading = false,
  label = 'Try again',
  className = '',
  disabled,
  ...props
}: RetryButtonProps) {
  return (
    <button
      type="button"
      className={['btn-secondary', className].filter(Boolean).join(' ')}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      ) : (
        <RotateCw className="h-4 w-4" aria-hidden="true" />
      )}
      {label}
    </button>
  )
}
