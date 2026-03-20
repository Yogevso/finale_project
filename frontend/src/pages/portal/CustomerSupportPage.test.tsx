/**
 * CustomerSupportPage test — X1-116: Customer ticket view and conversation
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import CustomerSupportPage from '@/pages/portal/CustomerSupportPage'
import type {
  SupportTicket,
  SupportTicketDetail,
  SupportTicketListResponse,
} from '@/types/chat'

// Mock auth (needed by optimistic update in CustomerTicketView)
vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 5, full_name: 'Jane Doe', role: 'customer' },
  }),
}))

// Mock API
const mockGetMyTickets = vi.fn()
const mockGetMyTicket = vi.fn()
const mockCreateMyTicket = vi.fn()
const mockSendMyTicketMessage = vi.fn()
const mockCloseMyTicket = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getMyTickets: (...args: unknown[]) => mockGetMyTickets(...args),
    getMyTicket: (...args: unknown[]) => mockGetMyTicket(...args),
    createMyTicket: (...args: unknown[]) => mockCreateMyTicket(...args),
    sendMyTicketMessage: (...args: unknown[]) => mockSendMyTicketMessage(...args),
    closeMyTicket: (...args: unknown[]) => mockCloseMyTicket(...args),
  },
}))

function buildTicket(overrides: Partial<SupportTicket> = {}): SupportTicket {
  return {
    id: 1,
    customer_id: 5,
    subject: 'Cannot upload file',
    status: 'open',
    priority: 'normal',
    category: null,
    feedback_id: null,
    tenant_id: 1,
    created_at: '2026-01-01T12:00:00Z',
    updated_at: '2026-01-01T12:00:00Z',
    resolved_at: null,
    customer_full_name: 'Jane Doe',
    ...overrides,
  }
}

function buildTicketDetail(overrides: Partial<SupportTicketDetail> = {}): SupportTicketDetail {
  return {
    ...buildTicket(),
    messages: [
      {
        id: 1,
        ticket_id: 1,
        sender_id: 5,
        sender_type: 'customer',
        content: 'I have a problem uploading',
        is_internal_note: false,
        created_at: '2026-01-01T12:00:00Z',
        sender_full_name: 'Jane Doe',
      },
      {
        id: 2,
        ticket_id: 1,
        sender_id: 10,
        sender_type: 'agent',
        content: 'We are looking into it',
        is_internal_note: false,
        created_at: '2026-01-01T12:05:00Z',
        sender_full_name: 'Agent Smith',
      },
      {
        id: 3,
        ticket_id: 1,
        sender_id: 10,
        sender_type: 'agent',
        content: 'Internal: check logs',
        is_internal_note: true,
        created_at: '2026-01-01T12:06:00Z',
        sender_full_name: 'Agent Smith',
      },
    ],
    assignments: [],
    ...overrides,
  }
}

function buildList(tickets: SupportTicket[]): SupportTicketListResponse {
  return { items: tickets, total: tickets.length, page: 1, page_size: 50 }
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CustomerSupportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetMyTickets.mockResolvedValue(buildList([]))
})

describe('CustomerSupportPage — ticket list', () => {
  it('renders heading and new ticket button', async () => {
    renderPage()
    expect(screen.getByText('Support')).toBeInTheDocument()
    expect(screen.getByText(/new ticket/i)).toBeInTheDocument()
  })

  it('shows empty state when no tickets', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/no support tickets yet/i)).toBeInTheDocument()
    })
  })

  it('renders ticket cards', async () => {
    mockGetMyTickets.mockResolvedValue(
      buildList([
        buildTicket({ id: 1, subject: 'Upload issue' }),
        buildTicket({ id: 2, subject: 'Login trouble', status: 'resolved' }),
      ]),
    )
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Upload issue')).toBeInTheDocument()
    })
    expect(screen.getByText('Login trouble')).toBeInTheDocument()
  })

  it('opens create ticket modal on button click', async () => {
    renderPage()
    fireEvent.click(screen.getByText(/new ticket/i))
    await waitFor(() => {
      expect(screen.getByText('New Support Ticket')).toBeInTheDocument()
    })
  })
})

describe('CustomerSupportPage — ticket detail', () => {
  beforeEach(() => {
    mockGetMyTickets.mockResolvedValue(buildList([buildTicket()]))
    mockGetMyTicket.mockResolvedValue(buildTicketDetail())
  })

  it('clicking a ticket shows its detail view', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })

    // Click the ticket card
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      // Ticket detail header shows subject
      expect(screen.getByText('I have a problem uploading')).toBeInTheDocument()
    })
  })

  it('filters out internal notes in customer view', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByText('We are looking into it')).toBeInTheDocument()
    })
    // Internal note should NOT be visible
    expect(screen.queryByText('Internal: check logs')).not.toBeInTheDocument()
  })

  it('shows agent name on agent messages', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByText('Agent Smith')).toBeInTheDocument()
    })
  })

  it('shows reply input when ticket is not closed', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/type your reply/i)).toBeInTheDocument()
    })
  })

  it('hides reply input when ticket is closed', async () => {
    mockGetMyTicket.mockResolvedValue(buildTicketDetail({ status: 'closed' }))
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByText('I have a problem uploading')).toBeInTheDocument()
    })
    expect(screen.queryByPlaceholderText(/type your reply/i)).not.toBeInTheDocument()
  })
})
