import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UsersPage from '@/pages/UsersPage'
import type {
  Company,
  CompanyListResponse,
  Invitation,
  InvitationListResponse,
  User,
} from '@/types'

const mockGetUsers = vi.fn()
const mockGetCompanies = vi.fn()
const mockGetInvitations = vi.fn()
const mockCreateUser = vi.fn()
const mockUpdateUser = vi.fn()
const mockDeleteUser = vi.fn()
const mockCancelInvitation = vi.fn()
const mockResendInvitation = vi.fn()
const mockCreateDirectChat = vi.fn()

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: {
      id: 10,
      full_name: 'Admin User',
      email: 'admin@example.com',
      username: 'admin',
      role: 'admin',
      is_active: true,
      tenant_id: 1,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    isManager: true,
  }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    getUsers: (...args: unknown[]) => mockGetUsers(...args),
    getCompanies: (...args: unknown[]) => mockGetCompanies(...args),
    getInvitations: (...args: unknown[]) => mockGetInvitations(...args),
    createUser: (...args: unknown[]) => mockCreateUser(...args),
    updateUser: (...args: unknown[]) => mockUpdateUser(...args),
    deleteUser: (...args: unknown[]) => mockDeleteUser(...args),
    cancelInvitation: (...args: unknown[]) => mockCancelInvitation(...args),
    resendInvitation: (...args: unknown[]) => mockResendInvitation(...args),
    createDirectChat: (...args: unknown[]) => mockCreateDirectChat(...args),
  },
}))

vi.mock('@/lib/toast', () => ({
  extractApiErrorMessage: (_error: unknown, fallback: string) => fallback,
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 22,
    email: 'jane@example.com',
    username: 'jane',
    full_name: 'Jane Doe',
    role: 'editor',
    is_active: true,
    tenant_id: 1,
    company_name: 'Acme Inc',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildCompany(overrides: Partial<Company> = {}): Company {
  return {
    id: 1,
    name: 'Acme Inc',
    slug: 'acme',
    is_active: true,
    company_type: 'customer',
    user_count: 3,
    owned_document_count: 0,
    assigned_document_count: 0,
    customer_visible_document_count: 0,
    document_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildInvitation(overrides: Partial<Invitation> = {}): Invitation {
  return {
    id: 77,
    email: 'invited@example.com',
    role: 'customer',
    tenant_id: 1,
    tenant_name: 'Acme Inc',
    invited_by: 10,
    inviter_name: 'Admin User',
    status: 'pending',
    expires_at: '2026-04-01T00:00:00Z',
    created_at: '2026-03-01T00:00:00Z',
    ...overrides,
  }
}

function buildCompanyListResponse(items: Company[]): CompanyListResponse {
  return {
    items,
    total: items.length,
    page: 1,
    per_page: items.length || 1,
    total_pages: 1,
  }
}

function buildInvitationListResponse(items: Invitation[]): InvitationListResponse {
  return {
    items,
    total: items.length,
    page: 1,
    per_page: 50,
    has_more: false,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetUsers.mockResolvedValue([buildUser()])
  mockGetCompanies.mockResolvedValue(buildCompanyListResponse([buildCompany()]))
  mockGetInvitations.mockResolvedValue(buildInvitationListResponse([buildInvitation()]))
  mockCreateUser.mockResolvedValue(
    buildUser({
      id: 99,
      username: 'new.user',
      email: 'new@example.com',
      full_name: 'New User',
      role: 'viewer',
    }),
  )
  mockUpdateUser.mockResolvedValue(buildUser())
  mockDeleteUser.mockResolvedValue(undefined)
  mockCancelInvitation.mockResolvedValue(undefined)
  mockResendInvitation.mockResolvedValue(undefined)
  mockCreateDirectChat.mockResolvedValue({ id: 501 })
})

describe('UsersPage', () => {
  it('renders users and pending invitations', async () => {
    renderPage()

    expect(screen.getByText('User Management')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument()
    })

    expect(screen.getByText('jane@example.com')).toBeInTheDocument()
    expect(screen.getByText('Pending Invitations')).toBeInTheDocument()
    expect(screen.getByText('invited@example.com')).toBeInTheDocument()
  })

  it('creates a user from the page dialog', async () => {
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /add user/i }))

    let dialog: HTMLElement
    await waitFor(() => {
      dialog = screen.getByRole('dialog', { name: /create user/i })
      expect(dialog).toBeInTheDocument()
    })

    dialog = screen.getByRole('dialog', { name: /create user/i })

    fireEvent.change(within(dialog).getByLabelText(/username/i), {
      target: { value: 'new.user' },
    })
    fireEvent.change(within(dialog).getByLabelText(/^password$/i), {
      target: { value: 'Password123!' },
    })
    fireEvent.change(within(dialog).getByLabelText(/^email$/i), {
      target: { value: 'new@example.com' },
    })
    fireEvent.change(within(dialog).getByLabelText(/full name/i), {
      target: { value: 'New User' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: /^create user$/i }))

    await waitFor(() => {
      expect(mockCreateUser).toHaveBeenCalledWith({
        email: 'new@example.com',
        username: 'new.user',
        full_name: 'New User',
        password: 'Password123!',
        role: 'viewer',
        tenant_id: undefined,
      })
    })
  })

  it('resends and cancels invitations from the page', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('invited@example.com')).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', { name: /resend invitation to invited@example\.com/i }),
    )

    await waitFor(() => {
      expect(mockResendInvitation).toHaveBeenCalledWith(77)
    })

    fireEvent.click(
      screen.getByRole('button', { name: /cancel invitation for invited@example\.com/i }),
    )
    fireEvent.click(screen.getByRole('button', { name: /^confirm$/i }))

    await waitFor(() => {
      expect(mockCancelInvitation).toHaveBeenCalledWith(77)
    })
  })
})
