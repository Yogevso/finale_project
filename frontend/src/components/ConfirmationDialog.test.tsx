import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ConfirmationDialog from '@/components/ConfirmationDialog'

describe('ConfirmationDialog', () => {
  it('focuses the cancel button by default when opened', () => {
    render(
      <ConfirmationDialog
        open
        title="Delete document"
        description="This action cannot be undone."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('keeps the cancel button operable while idle', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()

    render(
      <ConfirmationDialog
        open
        title="Deactivate company"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('traps tab focus inside the dialog', async () => {
    const user = userEvent.setup()

    render(
      <ConfirmationDialog
        open
        title="Archive document"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    const cancelButton = screen.getByRole('button', { name: 'Cancel' })
    const confirmButton = screen.getByRole('button', { name: 'Confirm' })

    expect(cancelButton).toHaveFocus()

    await user.tab()
    expect(confirmButton).toHaveFocus()

    await user.tab()
    expect(cancelButton).toHaveFocus()
  })
})
