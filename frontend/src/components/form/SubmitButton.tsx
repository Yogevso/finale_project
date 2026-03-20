import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Loader2 } from 'lucide-react'

type SubmitButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'

interface SubmitButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean
  loadingText?: string
  variant?: SubmitButtonVariant
}

const VARIANT_CLASS_NAMES: Record<SubmitButtonVariant, string> = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  danger: 'btn-danger',
  success: 'btn-success',
  ghost: 'btn-ghost',
}

export const SubmitButton = forwardRef<HTMLButtonElement, SubmitButtonProps>(function SubmitButton(
  {
    isLoading = false,
    loadingText,
    variant = 'primary',
    className = '',
    children,
    disabled,
    type = 'submit',
    ...props
  },
  ref,
) {
  return (
    <button
      {...props}
      ref={ref}
      type={type}
      disabled={disabled || isLoading}
      className={[VARIANT_CLASS_NAMES[variant], className].filter(Boolean).join(' ')}
    >
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
      {isLoading ? loadingText ?? children ?? 'Submitting...' : children}
    </button>
  )
})
