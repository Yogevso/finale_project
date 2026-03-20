import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from 'react'

interface FormFieldProps {
  label: string
  error?: string
  required?: boolean
  hint?: string
  children: ReactNode
  className?: string
  htmlFor?: string
}

export function FormField({
  label,
  error,
  required = false,
  hint,
  children,
  className = '',
  htmlFor,
}: FormFieldProps) {
  const generatedId = useId()
  const fieldId = htmlFor ?? generatedId
  const hintId = hint ? `${fieldId}-hint` : undefined
  const errorId = error ? `${fieldId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined
  const childProps = isValidElement(children)
    ? (children.props as {
        id?: string
        'aria-invalid'?: boolean
        'aria-describedby'?: string
      })
    : null

  const enhancedChild =
    isValidElement(children) &&
    typeof children.type === 'string' &&
    ['input', 'select', 'textarea'].includes(children.type)
      ? cloneElement(children as ReactElement<Record<string, unknown>>, {
          id: childProps?.id ?? fieldId,
          'aria-invalid': error ? true : childProps?.['aria-invalid'],
          'aria-describedby': [
            childProps?.['aria-describedby'],
            describedBy,
          ]
            .filter(Boolean)
            .join(' ') || undefined,
        })
      : children

  return (
    <div className={['space-y-1.5', className].filter(Boolean).join(' ')}>
      <label
        htmlFor={fieldId}
        className="block text-sm font-medium text-slate-700 dark:text-slate-200"
      >
        {label}
        {required ? <span className="ml-0.5 text-rose-500" aria-hidden="true">*</span> : null}
        {required ? <span className="sr-only"> required</span> : null}
      </label>
      {enhancedChild}
      {hint && !error ? (
        <p id={hintId} className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-xs text-rose-600 dark:text-rose-300" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
