import { forwardRef, useId, useState, type ChangeEvent, type InputHTMLAttributes } from 'react'
import { Eye, EyeOff } from 'lucide-react'

import { FormField } from './FormField'

type PasswordStrength = 'weak' | 'medium' | 'strong'

interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
  showStrengthMeter?: boolean
  wrapperClassName?: string
}

function getStrength(value: string): PasswordStrength {
  let score = 0
  if (value.length >= 8) score += 1
  if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score += 1
  if (/\d/.test(value) || /[^A-Za-z0-9]/.test(value)) score += 1

  if (score >= 3) return 'strong'
  if (score >= 2) return 'medium'
  return 'weak'
}

function getStrengthConfig(strength: PasswordStrength) {
  switch (strength) {
    case 'strong':
      return {
        label: 'Strong',
        textClassName: 'text-emerald-600 dark:text-emerald-400',
        fillClassNames: ['bg-emerald-500', 'bg-emerald-500', 'bg-emerald-500'],
      }
    case 'medium':
      return {
        label: 'Medium',
        textClassName: 'text-amber-600 dark:text-amber-400',
        fillClassNames: ['bg-amber-500', 'bg-amber-500', 'bg-slate-200 dark:bg-slate-700'],
      }
    default:
      return {
        label: 'Weak',
        textClassName: 'text-rose-600 dark:text-rose-400',
        fillClassNames: ['bg-rose-500', 'bg-slate-200 dark:bg-slate-700', 'bg-slate-200 dark:bg-slate-700'],
      }
  }
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(function PasswordInput(
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
    disabled,
    showStrengthMeter = true,
    ...props
  },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const [visible, setVisible] = useState(false)
  const [internalValue, setInternalValue] = useState(String(defaultValue ?? ''))

  const resolvedValue = typeof value === 'string' ? value : internalValue
  const strength = getStrength(resolvedValue)
  const strengthConfig = getStrengthConfig(strength)

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (typeof value !== 'string') {
      setInternalValue(event.target.value)
    }
    onChange?.(event)
  }

  const input = (
    <div className="space-y-2">
      <div className="relative">
        <input
          {...props}
          id={inputId}
          ref={ref}
          type={visible ? 'text' : 'password'}
          value={value}
          defaultValue={defaultValue}
          onChange={handleChange}
          disabled={disabled}
          required={required}
          aria-invalid={error ? true : undefined}
          className={[
            'input-field pr-11 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500',
            error ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500 motion-error-shake' : '',
            className,
          ].filter(Boolean).join(' ')}
        />
        <button
          type="button"
          aria-label={visible ? 'Hide password' : 'Show password'}
          disabled={disabled}
          onClick={() => setVisible((current) => !current)}
          className="absolute inset-y-0 right-2 flex items-center justify-center rounded-lg px-2 text-slate-500 transition hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 dark:text-slate-400 dark:hover:text-slate-100"
        >
          {visible ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
        </button>
      </div>
      {showStrengthMeter && resolvedValue ? (
        <div className="space-y-1">
          <div className="flex gap-2">
            {strengthConfig.fillClassNames.map((fillClassName, index) => (
              <div key={index} className={`h-1.5 flex-1 rounded-full ${fillClassName}`} />
            ))}
          </div>
          <p className={`text-xs font-medium ${strengthConfig.textClassName}`}>
            {strengthConfig.label} password
          </p>
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
        {input}
      </FormField>
    )
  }

  return input
})
