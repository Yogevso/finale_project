import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FormField } from './FormField'

describe('FormField', () => {
  it('wires hint text to native controls through aria-describedby', () => {
    render(
      <FormField label="Email address" htmlFor="email" hint="We will only use this for account updates.">
        <input type="email" />
      </FormField>,
    )

    const input = screen.getByLabelText(/email address/i)
    const hint = screen.getByText(/we will only use this for account updates/i)

    expect(input).toHaveAttribute('aria-describedby', hint.id)
  })

  it('marks native controls as invalid and announces field errors', () => {
    render(
      <FormField label="Full name" htmlFor="full-name" error="Full name is required">
        <input type="text" />
      </FormField>,
    )

    const input = screen.getByLabelText(/full name/i)
    const error = screen.getByRole('alert')

    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', error.id)
    expect(error).toHaveTextContent('Full name is required')
  })
})
