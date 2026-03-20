import { forwardRef, useId, useRef, useState, type ChangeEvent, type InputHTMLAttributes } from 'react'
import { Loader2, Search, X } from 'lucide-react'

interface SearchInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  isLoading?: boolean
  onClear?: () => void
  wrapperClassName?: string
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(function SearchInput(
  {
    id,
    className = '',
    wrapperClassName = '',
    value,
    defaultValue,
    onChange,
    onClear,
    isLoading = false,
    disabled,
    placeholder = 'Search...',
    ...props
  },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [internalValue, setInternalValue] = useState(String(defaultValue ?? ''))
  const resolvedValue = typeof value === 'string' ? value : internalValue

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (typeof value !== 'string') {
      setInternalValue(event.target.value)
    }
    onChange?.(event)
  }

  const clearValue = () => {
    if (disabled) {
      return
    }
    if (onClear) {
      onClear()
      return
    }
    if (typeof value === 'string') {
      const element = inputRef.current
      if (element) {
        const valueSetter = Object.getOwnPropertyDescriptor(
          HTMLInputElement.prototype,
          'value',
        )?.set
        valueSetter?.call(element, '')
        element.dispatchEvent(new Event('input', { bubbles: true }))
      }
      return
    }
    if (typeof value !== 'string') {
      setInternalValue('')
    }
  }

  return (
    <div className={['relative', wrapperClassName].filter(Boolean).join(' ')}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
      <input
        {...props}
        id={inputId}
        ref={(node) => {
          inputRef.current = node
          if (typeof ref === 'function') {
            ref(node)
          } else if (ref) {
            ref.current = node
          }
        }}
        type="search"
        value={value}
        defaultValue={defaultValue}
        onChange={handleChange}
        disabled={disabled}
        placeholder={placeholder}
        className={[
          'input-field pl-9 pr-10 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500',
          className,
        ].filter(Boolean).join(' ')}
      />
      <div className="absolute inset-y-0 right-3 flex items-center">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-slate-400" aria-hidden="true" />
        ) : resolvedValue ? (
          <button
            type="button"
            onClick={clearValue}
            aria-label="Clear search"
            className="rounded-full p-0.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </div>
  )
})
