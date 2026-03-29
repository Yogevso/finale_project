import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UsersPage from '@/pages/UsersPage'
import type {
  Company,
  CompanyListResponse,
  Invitation,
  InvitationEmailPreviewResponse,
  InvitationListResponse,
  User,
} from '@/types'

const mockGetUsers = vi.fn()
const mockGetCompanies = vi.fn()
const mockGetInvitations = vi.fn()
const mockGetInvitationEmailPreview = vi.fn()
const mockCreateUser = vi.fn()
const mockUpdateUser = vi.fn()
const mockDeleteUser = vi.fn()
const mockHardDeleteUser = vi.fn()
const mockCancelInvitation = vi.fn()
const mockResendInvitation = vi.fn()
const mockCreateDirectChat = vi.fn()

let mockAuthUser: User = {
  id: 10,
  full_name: 'Admin User',
  email: 'admin@example.com',
  username: 'admin',
  role: 'admin',
  is_active: true,
  tenant_id: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: mockAuthUser,
    isSystemAdmin: mockAuthUser.role === 'system_admin',
    isAdmin: mockAuthUser.role === 'admin' || mockAuthUser.role === 'system_admin',
    isManager: true,
  }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    getUsers: (...args: unknown[]) => mockGetUsers(...args),
    getCompanies: (...args: unknown[]) => mockGetCompanies(...args),
    getInvitations: (...args: unknown[]) => mockGetInvitations(...args),
    getInvitationEmailPreview: (...args: unknown[]) => mockGetInvitationEmailPreview(...args),
    createUser: (...args: unknown[]) => mockCreateUser(...args),
    updateUser: (...args: unknown[]) => mockUpdateUser(...args),
    deleteUser: (...args: unknown[]) => mockDeleteUser(...args),
    hardDeleteUser: (...args: unknown[]) => mockHardDeleteUser(...args),
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
    email_delivery_status: 'sent',
    email_delivery_attempt_count: 1,
    email_last_attempted_at: '2026-03-27T10:00:00Z',
    email_last_sent_at: '2026-03-27T10:00:01Z',
    email_last_error: null,
    email_last_subject: 'Admin User invited you to Documentation Platform',
    email_last_sender_email: 'mailer@example.com',
    email_last_sender_name: 'Mailer',
    ...overrides,
  }
}

function buildInvitationEmailPreviewResponse(
  overrides: Partial<InvitationEmailPreviewResponse> = {},
): InvitationEmailPreviewResponse {
  return {
    invitation_id: 77,
    email: 'invited@example.com',
    from_email: 'mailer@example.com',
    from_name: 'Mailer',
    subject: 'Admin User invited you to Documentation Platform',
    html_content: '<p>Preview body with preview-token-redacted</p>',
    text_content: 'Preview body with preview-token-redacted',
    preview_accept_url:
      'http://localhost:3000/invitation/accept?token=preview-token-redacted',
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
  mockAuthUser = {
    id: 10,
    full_name: 'Admin User',
    email: 'admin@example.com',
    username: 'admin',
    role: 'admin',
    is_active: true,
    tenant_id: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
  mockGetUsers.mockResolvedValue([buildUser()])
  mockGetCompanies.mockResolvedValue(buildCompanyListResponse([buildCompany()]))
  mockGetInvitations.mockResolvedValue(buildInvitationListResponse([buildInvitation()]))
  mockGetInvitationEmailPreview.mockResolvedValue(buildInvitationEmailPreviewResponse())
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
  mockHardDeleteUser.mockResolvedValue(undefined)
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
    expect(screen.getByText('sent')).toBeInTheDocument()
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

  it('deactivates a user from the table', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /deactivate jane doe/i }))
    fireEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))

    await waitFor(() => {
      expect(mockDeleteUser).toHaveBeenCalledWith(22)
    })
  })

  it('opens the invitation email preview dialog', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('invited@example.com')).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', { name: /preview invitation email for invited@example\.com/i }),
    )

    await waitFor(() => {
      expect(mockGetInvitationEmailPreview).toHaveBeenCalledWith(77)
    })

    expect(screen.getByRole('dialog', { name: /invitation email preview/i })).toBeInTheDocument()
    expect(screen.getByText('Mailer <mailer@example.com>')).toBeInTheDocument()
  })

  it('allows a system admin to permanently delete an inactive user', async () => {
    mockAuthUser = {
      ...mockAuthUser,
      role: 'system_admin',
    }
    mockGetUsers.mockResolvedValue([buildUser({ is_active: false })])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /permanently delete jane doe/i }))
    fireEvent.click(screen.getByRole('button', { name: /^delete permanently$/i }))

    await waitFor(() => {
      expect(mockHardDeleteUser).toHaveBeenCalledWith(22)
    })
  })
})
