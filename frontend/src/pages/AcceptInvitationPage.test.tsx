import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AcceptInvitationPage from '@/pages/AcceptInvitationPage'

const navigateMock = vi.fn()
const validateInvitationMock = vi.fn()
const acceptInvitationMock = vi.fn()
const setTokenMock = vi.fn()
const refreshUserMock = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useSearchParams: () => [new URLSearchParams('token=test-invite-token')],
  }
})

vi.mock('@/lib/api', () => ({
  api: {
    validateInvitation: (...args: unknown[]) => validateInvitationMock(...args),
    acceptInvitation: (...args: unknown[]) => acceptInvitationMock(...args),
    setToken: (...args: unknown[]) => setTokenMock(...args),
  },
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    refreshUser: (...args: unknown[]) => refreshUserMock(...args),
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

function renderPage() {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AcceptInvitationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AcceptInvitationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()

    validateInvitationMock.mockResolvedValue({
      valid: true,
      email: 'customer@example.com',
      role: 'customer',
      company_name: 'Acme Corp',
      inviter_name: 'Admin User',
    })
    acceptInvitationMock.mockResolvedValue({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
    })
    refreshUserMock.mockResolvedValue({
      id: 10,
      username: 'customer_user',
      role: 'customer',
    })
  })

  it('boots authenticated session through shared auth flow after accepting invitation', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByText(/Accept Invitation/i)

    await user.type(screen.getByPlaceholderText('Choose a username'), 'customer_user')
    await user.type(screen.getByPlaceholderText('Enter your full name'), 'Customer User')
    await user.type(screen.getByPlaceholderText('Create a password'), 'password123')
    await user.type(screen.getByPlaceholderText('Confirm your password'), 'password123')
    await user.click(screen.getByRole('button', { name: /Create Account/i }))

    await waitFor(() => {
      expect(setTokenMock).toHaveBeenCalledWith('access-token', 'refresh-token')
      expect(refreshUserMock).toHaveBeenCalledTimes(1)
      expect(navigateMock).toHaveBeenCalledWith('/portal')
    })

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })
})

