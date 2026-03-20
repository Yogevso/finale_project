import { forwardRef, useId, type SelectHTMLAttributes } from 'react'
import { Loader2 } from 'lucide-react'

import { FormField } from './FormField'

interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
  loading?: boolean
  options?: SelectOption[]
  placeholder?: string
  wrapperClassName?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  {
    id,
    label,
    error,
    hint,
    required = false,
    loading = false,
    options,
    placeholder,
    className = '',
    wrapperClassName = '',
    children,
    disabled,
    ...props
  },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? generatedId

  const content = (
    <div className="relative">
      <select
        {...props}
        id={inputId}
        ref={ref}
        disabled={disabled || loading}
        required={required}
        aria-invalid={error ? true : undefined}
        className={[
          'select-field pr-10 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100',
          error ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500 motion-error-shake' : '',
          className,
        ].filter(Boolean).join(' ')}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options?.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
        {children}
      </select>
      {loading ? (
        <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
          <Loader2 className="h-4 w-4 animate-spin text-slate-400" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  )

  if (label) {
    return (
      <FormField
        label={label}
        htmlFor={inputId}
        error={error}
        hint={hint}
        required={required}
        className={wrapperClassName}
      >
        {content}
      </FormField>
    )
  }

  return content
})
