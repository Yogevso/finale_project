import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import NotificationBell from '@/components/NotificationBell'

vi.mock('@/lib/api', () => ({
  api: {
    getNotifications: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      unread_count: 0,
    }),
    markNotificationRead: vi.fn().mockResolvedValue(undefined),
    markAllNotificationsRead: vi.fn().mockResolvedValue(undefined),
    deleteNotification: vi.fn().mockResolvedValue(undefined),
  },
}))

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function renderNotificationBellHarness() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <BrowserRouter>
        <div>
          <NotificationBell />
          <label htmlFor="notification-bell-focus-probe">Probe input</label>
          <input id="notification-bell-focus-probe" aria-label="Probe input" />
        </div>
      </BrowserRouter>
    </QueryClientProvider>,
  )
}

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
  })

  it('does not steal focus when the dropdown is closed and another field is clicked', async () => {
    const user = userEvent.setup()
    renderNotificationBellHarness()

    const bellButton = screen.getByRole('button', { name: /notifications/i })
    const probeInput = screen.getByRole('textbox', { name: /probe input/i })

    await user.click(probeInput)

    await waitFor(() => expect(probeInput).toHaveFocus())

    await user.type(probeInput, 'a')

    expect(probeInput).toHaveValue('a')
    expect(probeInput).toHaveFocus()
    expect(bellButton).not.toHaveFocus()
  })
})
