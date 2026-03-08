import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NotificationPreferences from './NotificationPreferences'

const updateMyNotificationPreferencesMock = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    updateMyNotificationPreferences: (...args: unknown[]) =>
      updateMyNotificationPreferencesMock(...args),
  },
}))

vi.mock('@/lib/toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

describe('NotificationPreferences', () => {
  beforeEach(() => {
    updateMyNotificationPreferencesMock.mockReset()
  })

  it('saves toggled notification preferences payload', async () => {
    const user = userEvent.setup()
    const queryClient = createQueryClient()
    const initialPreferences = {
      review_assigned: true,
      document_updated: false,
      mention: true,
    }
    const expectedPayload = {
      review_assigned: true,
      document_updated: true,
      mention: false,
    }

    updateMyNotificationPreferencesMock.mockResolvedValue(expectedPayload)

    render(
      <QueryClientProvider client={queryClient}>
        <NotificationPreferences initialPreferences={initialPreferences} />
      </QueryClientProvider>,
    )

    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[1])
    await user.click(checkboxes[2])
    await user.click(screen.getByRole('button', { name: /save preferences/i }))

    await waitFor(() => {
      expect(updateMyNotificationPreferencesMock).toHaveBeenCalledWith(expectedPayload)
    })
  })
})
