/**
 * CustomerSupportPage test — X1-116: Customer ticket view and conversation
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
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
const mockGetToken = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getMyTickets: (...args: unknown[]) => mockGetMyTickets(...args),
    getMyTicket: (...args: unknown[]) => mockGetMyTicket(...args),
    createMyTicket: (...args: unknown[]) => mockCreateMyTicket(...args),
    sendMyTicketMessage: (...args: unknown[]) => mockSendMyTicketMessage(...args),
    closeMyTicket: (...args: unknown[]) => mockCloseMyTicket(...args),
    getToken: () => mockGetToken(),
  },
}))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  send = vi.fn()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  emitOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new Event('close'))
  }
}

vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)

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
    last_customer_message_at: null,
    has_unread_activity: false,
    awaiting_agent_reply: false,
    needs_attention: false,
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
        content: 'We are looking into it',
        is_internal_note: false,
        file_url: null,
        file_name: null,
        file_size: null,
        file_mime_type: null,
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
        file_url: null,
        file_name: null,
        file_size: null,
        file_mime_type: null,
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

function renderPage(initialEntries = ['/portal/support']) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <CustomerSupportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  MockWebSocket.instances = []
  mockGetToken.mockReturnValue('test-token')
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

  it('opens a ticket directly from the query string', async () => {
    renderPage(['/portal/support?ticket=1'])

    await waitFor(() => {
      expect(screen.getByText('I have a problem uploading')).toBeInTheDocument()
    })

    expect(mockGetMyTicket).toHaveBeenCalledWith(1)
  })

  it('shows feedback-origin context when a support ticket started from feedback', async () => {
    mockGetMyTicket.mockResolvedValue(buildTicketDetail({ feedback_id: 88 }))
    renderPage(['/portal/support?ticket=1'])

    await waitFor(() => {
      expect(screen.getByText('Escalated from feedback')).toBeInTheDocument()
    })

    expect(
      screen.getByRole('link', { name: /view original feedback/i }),
    ).toHaveAttribute('href', '/portal/feedback?feedback=88')
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

  it('refreshes the active ticket when a websocket message arrives', async () => {
    const updatedDetail = buildTicketDetail({
      messages: [
        ...buildTicketDetail().messages,
        {
          id: 4,
          ticket_id: 1,
          sender_id: 10,
          sender_type: 'agent',
          content: 'Here is an update from support',
          is_internal_note: false,
          file_url: null,
          file_name: null,
          file_size: null,
          file_mime_type: null,
          created_at: '2026-01-01T12:07:00Z',
          sender_full_name: 'Agent Smith',
        },
      ],
    })
    mockGetMyTicket
      .mockResolvedValueOnce(buildTicketDetail())
      .mockResolvedValue(updatedDetail)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByText('We are looking into it')).toBeInTheDocument()
    })

    const socket = MockWebSocket.instances[0]
    await act(async () => {
      socket.emitOpen()
      socket.emitMessage({
        event: 'new_message',
        data: {
          ticket_id: 1,
          id: 4,
          sender_id: 10,
          sender_type: 'agent',
          content: 'Here is an update from support',
          is_internal_note: false,
          file_url: null,
          file_name: null,
          file_size: null,
          file_mime_type: null,
          created_at: '2026-01-01T12:07:00Z',
          sender_full_name: 'Agent Smith',
        },
      })
    })

    await waitFor(() => {
      expect(mockGetMyTicket).toHaveBeenCalledTimes(2)
      expect(screen.getByText('Here is an update from support')).toBeInTheDocument()
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

  it('renders attachment links on ticket messages', async () => {
    mockGetMyTicket.mockResolvedValue(
      buildTicketDetail({
        messages: [
          ...buildTicketDetail().messages,
          {
            id: 4,
            ticket_id: 1,
            sender_id: 10,
            sender_type: 'agent',
            content: 'See attached log',
            is_internal_note: false,
            file_url: '/api/v1/support/tickets/1/messages/4/attachment',
            file_name: 'error-log.txt',
            file_size: 2048,
            file_mime_type: 'text/plain',
            created_at: '2026-01-01T12:07:00Z',
            sender_full_name: 'Agent Smith',
          },
        ],
      }),
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /error-log\.txt/i })).toHaveAttribute(
        'href',
        '/api/v1/support/tickets/1/messages/4/attachment',
      )
    })
  })

  it('sends a reply with an attachment', async () => {
    mockSendMyTicketMessage.mockResolvedValue({
      id: 4,
      ticket_id: 1,
      sender_id: 5,
      sender_type: 'customer',
      content: 'Please see screenshot',
      is_internal_note: false,
      file_url: '/api/v1/support/tickets/1/messages/4/attachment',
      file_name: 'screenshot.png',
      file_size: 4,
      file_mime_type: 'image/png',
      created_at: '2026-01-01T12:08:00Z',
      sender_full_name: 'Jane Doe',
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Cannot upload file')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Cannot upload file'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/type your reply/i)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText(/type your reply/i), {
      target: { value: 'Please see screenshot' },
    })
    fireEvent.change(screen.getByLabelText(/attach a file/i, { selector: 'input' }), {
      target: {
        files: [new File(['png!'], 'screenshot.png', { type: 'image/png' })],
      },
    })
    fireEvent.click(screen.getByLabelText(/send reply/i))

    await waitFor(() => {
      expect(mockSendMyTicketMessage).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          content: 'Please see screenshot',
          file: expect.objectContaining({ name: 'screenshot.png' }),
        }),
      )
    })
  })
})
