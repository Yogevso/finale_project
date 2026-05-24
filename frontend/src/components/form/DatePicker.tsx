import { forwardRef, useId, useRef, type InputHTMLAttributes, type KeyboardEvent } from 'react'
import { CalendarDays } from 'lucide-react'

import { FormField } from './FormField'

interface DatePickerProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
  wrapperClassName?: string
}

export const DatePicker = forwardRef<HTMLInputElement, DatePickerProps>(function DatePicker(
  {
    id,
    label,
    error,
    hint,
    required = false,
    className = '',
    wrapperClassName = '',
    ...props
  },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const inputRef = useRef<HTMLInputElement | null>(null)

  const assignInputRef = (node: HTMLInputElement | null) => {
    inputRef.current = node

    if (typeof ref === 'function') {
      ref(node)
      return
    }

    if (ref) {
      ref.current = node
    }
  }

  const openPicker = () => {
    const input = inputRef.current
    if (!input) {
      return
    }

    input.focus()
    input.showPicker?.()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    props.onKeyDown?.(event)

    if (event.defaultPrevented || (event.key !== 'ArrowDown' && event.key !== 'Enter')) {
      return
    }

    const input = inputRef.current
    if (!input?.showPicker) {
      return
    }

    event.preventDefault()
    input.focus()
    input.showPicker()
  }

  const content = (
    <div className="relative">
      <input
        {...props}
        id={inputId}
        ref={assignInputRef}
        type="date"
        required={required}
        aria-invalid={error ? true : undefined}
        onKeyDown={handleKeyDown}
        className={[
          'input-field pr-11 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100',
          error ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500 motion-error-shake' : '',
          className,
        ].filter(Boolean).join(' ')}
      />
      <button
        type="button"
        onClick={openPicker}
        className="absolute inset-y-0 right-2 inline-flex items-center rounded-md px-1.5 text-slate-400 transition hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-slate-500 dark:hover:text-slate-300"
        aria-label={label ? `Open ${label}` : 'Open date picker'}
        disabled={props.disabled}
      >
        <CalendarDays className="h-4 w-4" aria-hidden="true" />
      </button>
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
