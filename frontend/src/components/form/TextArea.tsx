import {
  forwardRef,
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type TextareaHTMLAttributes,
} from 'react'

import { FormField } from './FormField'

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
  showCharacterCount?: boolean
  autoResize?: boolean
  wrapperClassName?: string
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  {
    id,
    label,
    error,
    hint,
    required = false,
    className = '',
    wrapperClassName = '',
    value,
    defaultValue,
    onChange,
    rows = 4,
    maxLength,
    showCharacterCount = true,
    autoResize = true,
    ...props
  },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const innerRef = useRef<HTMLTextAreaElement | null>(null)
  const [internalValue, setInternalValue] = useState(String(defaultValue ?? ''))
  const resolvedValue = typeof value === 'string' ? value : internalValue

  useEffect(() => {
    if (!autoResize || !innerRef.current) {
      return
    }

    innerRef.current.style.height = 'auto'
    innerRef.current.style.height = `${innerRef.current.scrollHeight}px`
  }, [autoResize, resolvedValue])

  const setRefs = (element: HTMLTextAreaElement | null) => {
    innerRef.current = element
    if (typeof ref === 'function') {
      ref(element)
    } else if (ref) {
      ref.current = element
    }
  }

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    if (typeof value !== 'string') {
      setInternalValue(event.target.value)
    }
    if (autoResize) {
      event.target.style.height = 'auto'
      event.target.style.height = `${event.target.scrollHeight}px`
    }
    onChange?.(event)
  }

  const content = (
    <div className="space-y-2">
      <textarea
        {...props}
        id={inputId}
        ref={setRefs}
        rows={rows}
        value={value}
        defaultValue={defaultValue}
        onChange={handleChange}
        required={required}
        aria-invalid={error ? true : undefined}
        className={[
          'input-field min-h-[7rem] resize-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500',
          error ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500 motion-error-shake' : '',
          className,
        ].filter(Boolean).join(' ')}
      />
      {showCharacterCount && typeof maxLength === 'number' ? (
        <p className="text-right text-xs text-slate-500 dark:text-slate-400">
          {resolvedValue.length}/{maxLength}
        </p>
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
