import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NewChatModal from '@/features/chat/NewChatModal'
import type { ChatEligibleUser } from '@/types/chat'

const mockGetChatEligibleUsers = vi.fn()
const mockCreateDirectChat = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getChatEligibleUsers: (...args: unknown[]) => mockGetChatEligibleUsers(...args),
    createDirectChat: (...args: unknown[]) => mockCreateDirectChat(...args),
  },
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: {
      id: 10,
      full_name: 'Editor User',
      email: 'editor@example.com',
      username: 'editor',
      role: 'editor',
      is_active: true,
      tenant_id: 1,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  }),
}))

vi.mock('@/hooks/useAccessibility', () => ({
  useFocusTrap: () => ({
    containerRef: { current: null },
  }),
}))

function buildEligibleUser(overrides: Partial<ChatEligibleUser> = {}): ChatEligibleUser {
  return {
    id: 7,
    email: 'customer@example.com',
    full_name: 'Customer Chat Target',
    role: 'customer',
    avatar_url: null,
    ...overrides,
  }
}

function renderModal() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const onClose = vi.fn()
  const onCreated = vi.fn()

  render(
    <QueryClientProvider client={queryClient}>
      <NewChatModal onClose={onClose} onCreated={onCreated} />
    </QueryClientProvider>,
  )

  return { onClose, onCreated }
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetChatEligibleUsers.mockResolvedValue([buildEligibleUser()])
  mockCreateDirectChat.mockResolvedValue({ id: 91 })
})

describe('NewChatModal', () => {
  it('loads eligible chat targets and starts a direct conversation', async () => {
    const { onCreated } = renderModal()

    await waitFor(() => {
      expect(mockGetChatEligibleUsers).toHaveBeenCalledWith({ search: undefined })
    })

    expect(await screen.findByText('Customer Chat Target')).toBeInTheDocument()
    expect(screen.getByText('Customer')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Customer Chat Target'))

    await waitFor(() => {
      expect(mockCreateDirectChat).toHaveBeenCalledWith({ user_id: 7 })
      expect(onCreated).toHaveBeenCalledWith(91)
    })
  })

  it('passes search terms to the eligible user query', async () => {
    renderModal()

    const searchInput = await screen.findByLabelText(/search people/i)
    fireEvent.change(searchInput, { target: { value: 'acme' } })

    await waitFor(() => {
      expect(mockGetChatEligibleUsers).toHaveBeenLastCalledWith({ search: 'acme' })
    })
  })
})
