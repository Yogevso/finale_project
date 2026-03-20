import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DatePicker } from './DatePicker'

describe('DatePicker', () => {
  const showPickerMock = vi.fn()

  beforeEach(() => {
    showPickerMock.mockReset()
    Object.defineProperty(HTMLInputElement.prototype, 'showPicker', {
      configurable: true,
      value: showPickerMock,
    })
  })

  afterEach(() => {
    Object.defineProperty(HTMLInputElement.prototype, 'showPicker', {
      configurable: true,
      value: undefined,
    })
  })

  it('opens the native picker from the calendar button', async () => {
    const user = userEvent.setup()

    render(<DatePicker label="Due date" />)

    await user.click(screen.getByRole('button', { name: /open due date/i }))

    expect(showPickerMock).toHaveBeenCalledTimes(1)
  })

  it('opens the native picker with keyboard shortcuts', () => {
    render(<DatePicker label="Due date" />)

    fireEvent.keyDown(screen.getByLabelText(/due date/i, { selector: 'input' }), { key: 'ArrowDown' })

    expect(showPickerMock).toHaveBeenCalledTimes(1)
  })
})
