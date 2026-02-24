import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from './auth'

const hasTokenMock = vi.fn()
const getCurrentUserMock = vi.fn()
const clearTokensMock = vi.fn()

vi.mock('./api', () => ({
  api: {
    hasToken: (...args: unknown[]) => hasTokenMock(...args),
    getCurrentUser: (...args: unknown[]) => getCurrentUserMock(...args),
    clearTokens: (...args: unknown[]) => clearTokensMock(...args),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function AuthProbe() {
  const { isLoading, hasPermission, canEditDocuments } = useAuth()
  if (isLoading) {
    return <div>loading</div>
  }

  return (
    <>
      <div data-testid="can-view-public">{String(hasPermission('view_public_docs'))}</div>
      <div data-testid="can-edit">{String(hasPermission('edit_document'))}</div>
      <div data-testid="can-edit-convenience">{String(canEditDocuments)}</div>
    </>
  )
}

describe('AuthProvider permissions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    hasTokenMock.mockReturnValue(true)
    getCurrentUserMock.mockResolvedValue({
      id: 1,
      email: 'editor@example.com',
      username: 'editor',
      full_name: 'Editor User',
      role: 'editor',
      is_active: true,
      tenant_id: 10,
      permissions: ['view_public_docs'],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    })
  })

  it('uses backend-provided effective permissions instead of static role matrix', async () => {
    const queryClient = createQueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AuthProbe />
        </AuthProvider>
      </QueryClientProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('can-view-public')).toHaveTextContent('true')
    })
    expect(screen.getByTestId('can-edit')).toHaveTextContent('false')
    expect(screen.getByTestId('can-edit-convenience')).toHaveTextContent('false')
  })
})
