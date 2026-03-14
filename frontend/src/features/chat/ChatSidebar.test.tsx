/**
 * ChatSidebar component tests — X1-057
 * Render chats, verify unread badges, search filter works
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChatSidebar from '@/features/chat/ChatSidebar'
import type { ChatListItem } from '@/types/chat'

function buildChatItem(overrides: Partial<ChatListItem> & { id?: number; name?: string } = {}): ChatListItem {
  const id = overrides.id ?? 1
  return {
    chat: {
      id,
      type: 'direct',
      name: overrides.name ?? null,
      created_by: 1,
      tenant_id: 1,
      last_message_at: '2026-01-01T12:00:00Z',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T12:00:00Z',
    },
    display_name: overrides.name ?? `Chat ${id}`,
    last_message: null,
    unread_count: overrides.unread_count ?? 0,
    is_muted: overrides.is_muted ?? false,
    ...overrides,
  }
}

const defaultProps = {
  activeChatId: null,
  searchFilter: '',
  onSearchChange: vi.fn(),
  onSelectChat: vi.fn(),
  onNewChat: vi.fn(),
}

describe('ChatSidebar', () => {
  it('renders chat list with display names', () => {
    const chats = [
      buildChatItem({ id: 1, name: 'Alice' }),
      buildChatItem({ id: 2, name: 'Bob' }),
    ]
    render(<ChatSidebar {...defaultProps} chats={chats} />)

    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  it('shows unread badge with correct count', () => {
    const chats = [buildChatItem({ id: 1, name: 'Alice', unread_count: 5 })]
    render(<ChatSidebar {...defaultProps} chats={chats} />)

    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('shows 99+ for large unread counts', () => {
    const chats = [buildChatItem({ id: 1, name: 'Alice', unread_count: 150 })]
    render(<ChatSidebar {...defaultProps} chats={chats} />)

    expect(screen.getByText('99+')).toBeInTheDocument()
  })

  it('does not show unread badge when count is 0', () => {
    const chats = [buildChatItem({ id: 1, name: 'Alice', unread_count: 0 })]
    render(<ChatSidebar {...defaultProps} chats={chats} />)

    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('fires onSearchChange when typing in search', () => {
    const onSearchChange = vi.fn()
    render(<ChatSidebar {...defaultProps} chats={[]} onSearchChange={onSearchChange} />)

    const input = screen.getByPlaceholderText(/search/i)
    fireEvent.change(input, { target: { value: 'hello' } })
    expect(onSearchChange).toHaveBeenCalledWith('hello')
  })

  it('fires onSelectChat when clicking a chat', () => {
    const onSelectChat = vi.fn()
    const chats = [buildChatItem({ id: 42, name: 'Alice' })]
    render(<ChatSidebar {...defaultProps} chats={chats} onSelectChat={onSelectChat} />)

    fireEvent.click(screen.getByText('Alice'))
    expect(onSelectChat).toHaveBeenCalledWith(42)
  })

  it('fires onNewChat when clicking new button', () => {
    const onNewChat = vi.fn()
    render(<ChatSidebar {...defaultProps} chats={[]} onNewChat={onNewChat} />)

    fireEvent.click(screen.getByText('+ New'))
    expect(onNewChat).toHaveBeenCalled()
  })

  it('shows empty state when no chats', () => {
    render(<ChatSidebar {...defaultProps} chats={[]} />)

    expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument()
  })

  it('renders last message preview', () => {
    const chats = [
      buildChatItem({
        id: 1,
        name: 'Alice',
        last_message: {
          id: 10,
          chat_id: 1,
          sender_id: 2,
          content: 'Hey there!',
          message_type: 'text',
          file_url: null,
          file_name: null,
          file_size: null,
          file_mime_type: null,
          created_at: '2026-01-01T12:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          sender_full_name: 'Alice',
        },
      }),
    ]
    render(<ChatSidebar {...defaultProps} chats={chats} />)

    expect(screen.getByText('Hey there!')).toBeInTheDocument()
  })
})
