import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import ChatView from '@/features/chat/ChatView'
import type { ChatDetail, ChatMessage } from '@/types/chat'

vi.mock('@emoji-mart/data', () => ({ default: {} }))
vi.mock('@emoji-mart/react', () => ({
  default: () => <div data-testid="emoji-picker" />,
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, full_name: 'Alex Agent' },
  }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    searchChatMessages: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

function renderChatView(messages: ChatMessage[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  const chat: ChatDetail = {
    id: 10,
    type: 'direct',
    name: null,
    created_by: 1,
    tenant_id: 1,
    last_message_at: '2026-01-01T12:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T12:00:00Z',
    participants: [
      {
        id: 1,
        user_id: 1,
        role: 'owner',
        joined_at: '2026-01-01T00:00:00Z',
        last_read_at: '2026-01-01T12:00:00Z',
        is_muted: false,
        user_full_name: 'Alex Agent',
      },
      {
        id: 2,
        user_id: 2,
        role: 'member',
        joined_at: '2026-01-01T00:00:00Z',
        last_read_at: '2026-01-01T12:00:00Z',
        is_muted: false,
        user_full_name: 'Jordan Customer',
      },
    ],
  }

  return render(
    <QueryClientProvider client={queryClient}>
      <ChatView
        chat={chat}
        messages={messages}
        displayName="Jordan Customer"
        typingText=""
        isConnected
        isLoading={false}
        onSend={vi.fn()}
        onTyping={vi.fn()}
        onClose={vi.fn()}
      />
    </QueryClientProvider>,
  )
}

describe('ChatView accessibility', () => {
  it('exposes the message list as a polite log region', () => {
    renderChatView([
      {
        id: 1,
        chat_id: 10,
        sender_id: 2,
        content: 'Hello there',
        message_type: 'text',
        file_url: null,
        file_name: null,
        file_size: null,
        file_mime_type: null,
        created_at: '2026-01-01T12:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
        sender_full_name: 'Jordan Customer',
      },
    ])

    expect(screen.getByRole('log', { name: /jordan customer conversation messages/i })).toHaveAttribute(
      'aria-live',
      'polite',
    )
  })
})
