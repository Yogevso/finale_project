import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NpsWidget from '@/components/NpsWidget'

const portalApiMocks = vi.hoisted(() => ({
  getNpsStatus: vi.fn(),
  submitNps: vi.fn(),
}))

vi.mock('@/lib/portalApi', () => ({
  portalApi: portalApiMocks,
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: {
      id: 42,
      role: 'customer',
    },
  }),
}))

function renderWidget() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NpsWidget />
    </QueryClientProvider>,
  )
}

describe('NpsWidget', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    portalApiMocks.getNpsStatus.mockResolvedValue({ should_show: true })
    portalApiMocks.submitNps.mockResolvedValue(undefined)
  })

  it('persists dismissal across remounts for the current user', async () => {
    const user = userEvent.setup()
    const { unmount } = renderWidget()

    await waitFor(() => {
      expect(screen.getByText(/Quick Survey/i)).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /dismiss survey/i }))

    expect(screen.queryByText(/Quick Survey/i)).not.toBeInTheDocument()
    expect(localStorage.getItem('nps-widget-dismissed-42')).not.toBeNull()

    unmount()
    renderWidget()

    await waitFor(() => {
      expect(portalApiMocks.getNpsStatus).toHaveBeenCalled()
    })

    expect(screen.queryByText(/Quick Survey/i)).not.toBeInTheDocument()
  })
})
