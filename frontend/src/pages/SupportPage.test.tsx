/**
 * SupportPage test — X1-115: Agent dashboard renders tickets, filters, counts
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SupportPage from '@/pages/SupportPage'
import type { SupportTicket, SupportTicketDetail, SupportTicketListResponse } from '@/types/chat'

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
const mockSendSupportTicketMessage = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getSupportTickets: (...args: unknown[]) => mockGetSupportTickets(...args),
    getSupportTicket: (...args: unknown[]) => mockGetSupportTicket(...args),
    getTicketViewers: (...args: unknown[]) => mockGetTicketViewers(...args),
    getUsers: (...args: unknown[]) => mockGetUsers(...args),
    sendSupportTicketMessage: (...args: unknown[]) => mockSendSupportTicketMessage(...args),
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

function buildTicketDetail(overrides: Partial<SupportTicketDetail> = {}): SupportTicketDetail {
  return {
    ...buildTicket(),
    messages: [
      {
        id: 1,
        ticket_id: 1,
        sender_id: 5,
        sender_type: 'customer',
        content: 'Need help with upload',
        is_internal_note: false,
        file_url: null,
        file_name: null,
        file_size: null,
        file_mime_type: null,
        created_at: '2026-01-01T12:00:00Z',
        sender_full_name: 'Jane Doe',
      },
      {
        id: 2,
        ticket_id: 1,
        sender_id: 10,
        sender_type: 'agent',
        content: 'Checking this now',
        is_internal_note: false,
        file_url: null,
        file_name: null,
        file_size: null,
        file_mime_type: null,
        created_at: '2026-01-01T12:05:00Z',
        sender_full_name: 'Agent Smith',
      },
    ],
    assignments: [],
    ...overrides,
  }
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
  mockGetTicketViewers.mockResolvedValue({ ticket_id: 1, viewer_ids: [10] })
  mockGetUsers.mockResolvedValue([])
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

  it('renders attachment links in ticket detail', async () => {
    mockGetSupportTickets.mockResolvedValue(buildTicketList([buildTicket()]))
    mockGetSupportTicket.mockResolvedValue(
      buildTicketDetail({
        messages: [
          ...buildTicketDetail().messages,
          {
            id: 3,
            ticket_id: 1,
            sender_id: 10,
            sender_type: 'agent',
            content: 'See attached log',
            is_internal_note: false,
            file_url: '/api/v1/support/tickets/1/messages/3/attachment',
            file_name: 'error-log.txt',
            file_size: 2048,
            file_mime_type: 'text/plain',
            created_at: '2026-01-01T12:06:00Z',
            sender_full_name: 'Agent Smith',
          },
        ],
      }),
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Need help with upload')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Need help with upload'))

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /error-log\.txt/i })).toHaveAttribute(
        'href',
        '/api/v1/support/tickets/1/messages/3/attachment',
      )
    })
  })

  it('sends an agent reply with an attachment', async () => {
    mockGetSupportTickets.mockResolvedValue(buildTicketList([buildTicket()]))
    mockGetSupportTicket.mockResolvedValue(buildTicketDetail())
    mockSendSupportTicketMessage.mockResolvedValue({
      id: 3,
      ticket_id: 1,
      sender_id: 10,
      sender_type: 'agent',
      content: 'Please review the log',
      is_internal_note: false,
      file_url: '/api/v1/support/tickets/1/messages/3/attachment',
      file_name: 'support-log.txt',
      file_size: 4,
      file_mime_type: 'text/plain',
      created_at: '2026-01-01T12:06:00Z',
      sender_full_name: 'Agent Smith',
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Need help with upload')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Need help with upload'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/reply to customer/i)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText(/reply to customer/i), {
      target: { value: 'Please review the log' },
    })
    fireEvent.change(screen.getByLabelText(/attach a file/i), {
      target: {
        files: [new File(['log!'], 'support-log.txt', { type: 'text/plain' })],
      },
    })
    fireEvent.click(screen.getByRole('button', { name: /send reply/i }))

    await waitFor(() => {
      expect(mockSendSupportTicketMessage).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          content: 'Please review the log',
          file: expect.objectContaining({ name: 'support-log.txt' }),
        }),
      )
    })
  })
})
