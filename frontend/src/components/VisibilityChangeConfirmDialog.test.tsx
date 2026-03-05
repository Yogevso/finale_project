import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

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
})
