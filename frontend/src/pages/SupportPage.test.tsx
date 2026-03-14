/**
 * SupportPage test — X1-115: Agent dashboard renders tickets, filters, counts
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SupportPage from '@/pages/SupportPage'
import type { SupportTicket, SupportTicketListResponse } from '@/types/chat'

// Mock auth
vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 10, full_name: 'Agent Smith', role: 'admin' },
  }),
}))

// Mock API
const mockGetSupportTickets = vi.fn()
const mockGetSupportTicket = vi.fn()
const mockGetTicketViewers = vi.fn()
const mockGetUsers = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getSupportTickets: (...args: unknown[]) => mockGetSupportTickets(...args),
    getSupportTicket: (...args: unknown[]) => mockGetSupportTicket(...args),
    getTicketViewers: (...args: unknown[]) => mockGetTicketViewers(...args),
    getUsers: (...args: unknown[]) => mockGetUsers(...args),
    sendSupportTicketMessage: vi.fn(),
    updateSupportTicket: vi.fn(),
    assignSupportAgent: vi.fn(),
    unassignSupportAgent: vi.fn(),
    handoffTicket: vi.fn(),
    getCannedResponses: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}))

function buildTicket(overrides: Partial<SupportTicket> = {}): SupportTicket {
  return {
    id: 1,
    customer_id: 5,
    subject: 'Need help with upload',
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

function buildTicketList(tickets: SupportTicket[]): SupportTicketListResponse {
  return { items: tickets, total: tickets.length, page: 1, page_size: 50 }
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SupportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetSupportTickets.mockResolvedValue(buildTicketList([]))
})

describe('SupportPage — ticket list', () => {
  it('renders page header', async () => {
    renderPage()
    expect(screen.getByText('Support')).toBeInTheDocument()
    expect(screen.getByText(/manage customer support tickets/i)).toBeInTheDocument()
  })

  it('shows "No tickets found" when empty', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No tickets found')).toBeInTheDocument()
    })
  })

  it('renders ticket rows', async () => {
    mockGetSupportTickets.mockResolvedValue(
      buildTicketList([
        buildTicket({ id: 1, subject: 'Bug report A', status: 'open' }),
        buildTicket({ id: 2, subject: 'Feature request B', status: 'resolved' }),
      ]),
    )
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Bug report A')).toBeInTheDocument()
    })
    expect(screen.getByText('Feature request B')).toBeInTheDocument()
    expect(screen.getByText('2 ticket(s)')).toBeInTheDocument()
  })

  it('displays customer name and priority badges', async () => {
    mockGetSupportTickets.mockResolvedValue(
      buildTicketList([buildTicket({ priority: 'urgent', customer_full_name: 'Jane Doe' })]),
    )
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument()
    })
    expect(screen.getByText('urgent')).toBeInTheDocument()
  })

  it('status filter select has all options', () => {
    renderPage()
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()

    const options = screen.getAllByRole('option')
    const texts = options.map((o) => o.textContent)
    expect(texts).toEqual(
      expect.arrayContaining(['All statuses', 'Open', 'In Progress', 'Resolved', 'Closed']),
    )
  })

  it('changing status filter re-fetches with filter param', async () => {
    renderPage()

    await waitFor(() => {
      expect(mockGetSupportTickets).toHaveBeenCalled()
    })

    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'open' } })

    await waitFor(() => {
      expect(mockGetSupportTickets).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'open' }),
      )
    })
  })
})
