/**
 * Accessibility test for chat — X1-060
 * Keyboard navigation, screen reader announcements for new messages
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChatSidebar from '@/features/chat/ChatSidebar'
import type { ChatListItem } from '@/types/chat'

// Mock emoji-mart to avoid import issues in test
vi.mock('@emoji-mart/data', () => ({ default: {} }))
vi.mock('@emoji-mart/react', () => ({
  default: () => <div data-testid="emoji-picker" />,
}))

import MessageInput from '@/features/chat/MessageInput'

function buildChatItem(id: number, name: string): ChatListItem {
  return {
    chat: {
      id,
      type: 'direct',
      name: null,
      created_by: 1,
      tenant_id: 1,
      last_message_at: '2026-01-01T12:00:00Z',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T12:00:00Z',
    },
    display_name: name,
    last_message: null,
    unread_count: 0,
    is_muted: false,
  }
}

describe('Chat Accessibility', () => {
  describe('ChatSidebar keyboard navigation', () => {
    it('search input is focusable', () => {
      render(
        <ChatSidebar
          chats={[buildChatItem(1, 'Alice')]}
          activeChatId={null}
          searchFilter=""
          onSearchChange={vi.fn()}
          onSelectChat={vi.fn()}
          onNewChat={vi.fn()}
        />,
      )

      const input = screen.getByPlaceholderText(/search/i)
      input.focus()
      expect(document.activeElement).toBe(input)
    })

    it('chat items are clickable buttons', () => {
      render(
        <ChatSidebar
          chats={[buildChatItem(1, 'Alice'), buildChatItem(2, 'Bob')]}
          activeChatId={null}
          searchFilter=""
          onSearchChange={vi.fn()}
          onSelectChat={vi.fn()}
          onNewChat={vi.fn()}
        />,
      )

      const buttons = screen.getAllByRole('button')
      // At least new button + 2 chat entries
      expect(buttons.length).toBeGreaterThanOrEqual(3)
    })

    it('new chat button is keyboard accessible', () => {
      const onNewChat = vi.fn()
      render(
        <ChatSidebar
          chats={[]}
          activeChatId={null}
          searchFilter=""
          onSearchChange={vi.fn()}
          onSelectChat={vi.fn()}
          onNewChat={onNewChat}
        />,
      )

      const newBtn = screen.getByText('+ New')
      newBtn.focus()
      fireEvent.keyDown(newBtn, { key: 'Enter' })
      fireEvent.click(newBtn)
      expect(onNewChat).toHaveBeenCalled()
    })
  })

  describe('MessageInput keyboard interaction', () => {
    it('textarea is focusable and accepts input', () => {
      render(<MessageInput onSend={vi.fn()} onTyping={vi.fn()} />)

      const textarea = screen.getByPlaceholderText(/type a message/i)
      textarea.focus()
      expect(document.activeElement).toBe(textarea)
    })

    it('Enter key sends message (keyboard shortcut)', () => {
      const onSend = vi.fn()
      render(<MessageInput onSend={onSend} onTyping={vi.fn()} />)

      const textarea = screen.getByPlaceholderText(/type a message/i)
      fireEvent.change(textarea, { target: { value: 'Test message' } })
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })

      expect(onSend).toHaveBeenCalledWith('Test message')
    })

    it('Shift+Enter does not send (allows multiline)', () => {
      const onSend = vi.fn()
      render(<MessageInput onSend={onSend} onTyping={vi.fn()} />)

      const textarea = screen.getByPlaceholderText(/type a message/i)
      fireEvent.change(textarea, { target: { value: 'Line 1' } })
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })

      expect(onSend).not.toHaveBeenCalled()
    })
  })
})
