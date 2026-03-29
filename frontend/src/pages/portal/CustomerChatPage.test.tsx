import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import CustomerChatPage from '@/pages/portal/CustomerChatPage'
import type { ChatDetail, ChatListResponse, ChatMessageListResponse } from '@/types/chat'

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 5, full_name: 'Jane Doe', role: 'customer' },
  }),
}))

const mockGetPortalChats = vi.fn()
const mockGetPortalChatDetail = vi.fn()
const mockGetPortalChatMessages = vi.fn()
const mockMarkPortalChatAsRead = vi.fn()
const mockGetToken = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getPortalChats: (...args: unknown[]) => mockGetPortalChats(...args),
    getPortalChatDetail: (...args: unknown[]) => mockGetPortalChatDetail(...args),
    getPortalChatMessages: (...args: unknown[]) => mockGetPortalChatMessages(...args),
    markPortalChatAsRead: (...args: unknown[]) => mockMarkPortalChatAsRead(...args),
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
Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
  configurable: true,
  value: vi.fn(),
})

function buildChats(): ChatListResponse {
  return {
    items: [
      {
        chat: {
          id: 7,
          type: 'direct',
          name: null,
          created_by: 11,
          tenant_id: 1,
          last_message_at: '2026-03-27T10:00:00Z',
          created_at: '2026-03-27T09:00:00Z',
          updated_at: '2026-03-27T10:00:00Z',
        },
        display_name: 'Portal Manager',
        last_message: {
          id: 10,
          chat_id: 7,
          sender_id: 11,
          content: 'Checking in',
          message_type: 'text',
          file_url: null,
          file_name: null,
          file_size: null,
          file_mime_type: null,
          created_at: '2026-03-27T10:00:00Z',
          updated_at: '2026-03-27T10:00:00Z',
          sender_full_name: 'Portal Manager',
        },
        unread_count: 1,
        is_muted: false,
      },
    ],
    total: 1,
  }
}

function buildChatDetail(): ChatDetail {
  return {
    id: 7,
    type: 'direct',
    name: null,
    created_by: 11,
    tenant_id: 1,
    last_message_at: '2026-03-27T10:00:00Z',
    created_at: '2026-03-27T09:00:00Z',
    updated_at: '2026-03-27T10:00:00Z',
    participants: [
      {
        id: 1,
        user_id: 5,
        role: 'owner',
        joined_at: '2026-03-27T09:00:00Z',
        last_read_at: null,
        is_muted: false,
        user_full_name: 'Jane Doe',
      },
      {
        id: 2,
        user_id: 11,
        role: 'member',
        joined_at: '2026-03-27T09:00:00Z',
        last_read_at: null,
        is_muted: false,
        user_full_name: 'Portal Manager',
      },
    ],
  }
}

function buildMessages(): ChatMessageListResponse {
  return {
    items: [
      {
        id: 10,
        chat_id: 7,
        sender_id: 11,
        content: 'Checking in',
        message_type: 'text',
        file_url: null,
        file_name: null,
        file_size: null,
        file_mime_type: null,
        created_at: '2026-03-27T10:00:00Z',
        updated_at: '2026-03-27T10:00:00Z',
        sender_full_name: 'Portal Manager',
      },
    ],
    has_more: false,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CustomerChatPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  MockWebSocket.instances = []
  mockGetToken.mockReturnValue('portal-chat-token')
  mockGetPortalChats.mockResolvedValue(buildChats())
  mockGetPortalChatDetail.mockResolvedValue(buildChatDetail())
  mockGetPortalChatMessages.mockResolvedValue(buildMessages())
  mockMarkPortalChatAsRead.mockResolvedValue(undefined)
})

describe('CustomerChatPage', () => {
  it('renders the customer chat list and opens a conversation', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Portal Manager')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Portal Manager'))

    await waitFor(() => {
      expect(screen.getByText('Checking in')).toBeInTheDocument()
    })
    expect(mockGetPortalChatDetail).toHaveBeenCalledWith(7)
    expect(mockGetPortalChatMessages).toHaveBeenCalledWith(7)
  })

  it('sends websocket messages from the customer conversation', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Portal Manager')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Portal Manager'))

    await waitFor(() => {
      expect(screen.getAllByText('Checking in').length).toBeGreaterThan(0)
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const socket = MockWebSocket.instances[0]
    await act(async () => {
      socket.emitOpen()
    })

    await waitFor(() => {
      expect(mockMarkPortalChatAsRead).toHaveBeenCalledWith(7)
    })

    const composer = screen.getByRole('textbox')
    fireEvent.change(composer, {
      target: { value: 'Customer reply' },
    })
    const sendButton = screen.getByLabelText(/send message/i)
    await waitFor(() => {
      expect(composer).toHaveValue('Customer reply')
      expect(sendButton).not.toBeDisabled()
    })
    fireEvent.click(sendButton)

    expect(socket.send).toHaveBeenLastCalledWith(
      JSON.stringify({ event: 'send_message', data: { chat_id: 7, content: 'Customer reply' } }),
    )
  })

  it('appends new websocket messages into the active conversation', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Portal Manager')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Portal Manager'))

    await waitFor(() => {
      expect(screen.getByText('Checking in')).toBeInTheDocument()
    })

    const socket = MockWebSocket.instances[0]
    await act(async () => {
      socket.emitOpen()
      socket.emitMessage({
        event: 'new_message',
        data: {
          id: 12,
          chat_id: 7,
          sender_id: 11,
          sender_full_name: 'Portal Manager',
          content: 'Here is the latest update',
          message_type: 'text',
          created_at: '2026-03-27T10:02:00Z',
          updated_at: '2026-03-27T10:02:00Z',
          file_url: null,
          file_name: null,
          file_size: null,
          file_mime_type: null,
        },
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Here is the latest update')).toBeInTheDocument()
    })
  })
})
