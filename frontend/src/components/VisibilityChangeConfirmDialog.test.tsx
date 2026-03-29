import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { COMMUNICATION_INPUT_LIMITS } from '@/lib/uiInputRules'
import VisibilityChangeConfirmDialog from './VisibilityChangeConfirmDialog'

describe('VisibilityChangeConfirmDialog', () => {
  it('requires a non-empty reason before allowing submit', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    render(
      <VisibilityChangeConfirmDialog
        isOpen={true}
        fromVisibility="internal"
        toVisibility="public"
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    )

    const confirmButton = screen.getByRole('button', { name: /confirm change/i })
    expect(confirmButton).toBeDisabled()

    const reasonInput = screen.getByTestId('visibility-change-reason')
    await user.type(reasonInput, 'ok')
    expect(confirmButton).toBeDisabled()

    await user.clear(reasonInput)
    await user.type(reasonInput, 'Share with public support channels')
    expect(confirmButton).toBeEnabled()

    await user.click(confirmButton)
    expect(onConfirm).toHaveBeenCalledWith({
      reason: 'Share with public support channels',
      companyIds: undefined,
    })
  })

  it('caps the reason field to the documented audit limit', () => {
    render(
      <VisibilityChangeConfirmDialog
        isOpen={true}
        fromVisibility="internal"
        toVisibility="public"
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )

    const reasonInput = screen.getByTestId('visibility-change-reason')
    expect(reasonInput).toHaveAttribute(
      'maxLength',
      String(COMMUNICATION_INPUT_LIMITS.visibilityReason),
    )
    expect(
      screen.getByText(`Minimum 3 characters. Reason is stored in the audience audit trail. 0/${COMMUNICATION_INPUT_LIMITS.visibilityReason}`),
    ).toBeInTheDocument()
  })
})
