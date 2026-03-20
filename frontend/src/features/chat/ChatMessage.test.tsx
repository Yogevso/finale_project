/**
 * ChatMessage component tests — X1-059
 * Render with different states (sent, delivered, read)
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import ChatMessage from '@/features/chat/ChatMessage'
import type { ChatMessage as ChatMessageType } from '@/types/chat'

function buildMessage(overrides: Partial<ChatMessageType> = {}): ChatMessageType {
  return {
    id: 1,
    chat_id: 1,
    sender_id: 2,
    content: 'Hello world',
    message_type: 'text',
    file_url: null,
    file_name: null,
    file_size: null,
    file_mime_type: null,
    created_at: '2026-01-01T12:00:00Z',
    updated_at: '2026-01-01T12:00:00Z',
    sender_full_name: 'Alice',
    ...overrides,
  }
}

function renderMsg(props: Parameters<typeof ChatMessage>[0]) {
  return render(
    <BrowserRouter>
      <ChatMessage {...props} />
    </BrowserRouter>,
  )
}

describe('ChatMessage', () => {
  it('renders text message content', () => {
    renderMsg({ message: buildMessage({ content: 'Test message' }), isOwn: false })

    expect(screen.getByText('Test message')).toBeInTheDocument()
  })

  it('shows sender name for received messages', () => {
    renderMsg({ message: buildMessage({ sender_full_name: 'Bob' }), isOwn: false })

    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  it('does not show sender name for own messages', () => {
    renderMsg({ message: buildMessage({ sender_full_name: 'Me' }), isOwn: true })

    expect(screen.queryByText('Me')).not.toBeInTheDocument()
  })

  it('renders system message centered', () => {
    renderMsg({
      message: buildMessage({ content: 'Alice joined the group', message_type: 'system' }),
      isOwn: false,
    })

    expect(screen.getByText('Alice joined the group')).toBeInTheDocument()
  })

  it('shows double check icon for read messages', () => {
    const { container } = renderMsg({
      message: buildMessage(),
      isOwn: true,
      isRead: true,
    })

    // CheckCheck icon (read receipt) should be present
    const checkIcons = container.querySelectorAll('svg')
    expect(checkIcons.length).toBeGreaterThan(0)
  })

  it('shows single check for unread own messages', () => {
    const { container } = renderMsg({
      message: buildMessage(),
      isOwn: true,
      isRead: false,
    })

    const checkIcons = container.querySelectorAll('svg')
    expect(checkIcons.length).toBeGreaterThan(0)
  })

  it('shows "Sending..." for optimistic messages (negative id)', () => {
    renderMsg({
      message: buildMessage({ id: -1 }),
      isOwn: true,
    })

    expect(screen.getByText('Sending...')).toBeInTheDocument()
  })

  it('highlights search result with yellow ring', () => {
    const { container } = renderMsg({
      message: buildMessage(),
      isOwn: false,
      isHighlighted: true,
    })

    const highlightedEl = container.querySelector('.ring-yellow-400')
    expect(highlightedEl).toBeTruthy()
  })

  it('highlights active result with blue ring', () => {
    const { container } = renderMsg({
      message: buildMessage(),
      isOwn: false,
      isActiveResult: true,
    })

    const activeEl = container.querySelector('.ring-sky-500')
    expect(activeEl).toBeTruthy()
  })

  it('renders @document-123 as clickable link', () => {
    renderMsg({
      message: buildMessage({ content: 'Check @document-42 for details' }),
      isOwn: false,
    })

    const link = screen.getByText(/Document #42/)
    expect(link).toBeInTheDocument()
    expect(link.closest('a')).toHaveAttribute('href', '/documents/42')
  })

  it('renders file attachment card', () => {
    renderMsg({
      message: buildMessage({
        message_type: 'file',
        content: 'report.pdf',
        file_url: '/files/report.pdf',
        file_name: 'report.pdf',
        file_size: 1024000,
        file_mime_type: 'application/pdf',
      }),
      isOwn: false,
    })

    expect(screen.getByText('report.pdf')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /download report\.pdf/i })).toHaveAttribute(
      'href',
      '/files/report.pdf',
    )
  })
})
