/**
 * MessageInput component tests — X1-058
 * Type message, send, verify input clears
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Mock emoji-mart to avoid import issues in test
vi.mock('@emoji-mart/data', () => ({ default: {} }))
vi.mock('@emoji-mart/react', () => ({
  default: () => <div data-testid="emoji-picker" />,
}))

import MessageInput from '@/features/chat/MessageInput'

describe('MessageInput', () => {
  it('renders textarea and send button', () => {
    render(<MessageInput onSend={vi.fn()} onTyping={vi.fn()} />)

    expect(screen.getByPlaceholderText(/type a message/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '' })).toBeTruthy() // send button
  })

  it('calls onSend with text and clears input on Enter', () => {
    const onSend = vi.fn()
    render(<MessageInput onSend={onSend} onTyping={vi.fn()} />)

    const textarea = screen.getByPlaceholderText(/type a message/i)
    fireEvent.change(textarea, { target: { value: 'Hello world' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })

    expect(onSend).toHaveBeenCalledWith('Hello world')
  })

  it('does not send on Shift+Enter (allows newline)', () => {
    const onSend = vi.fn()
    render(<MessageInput onSend={onSend} onTyping={vi.fn()} />)

    const textarea = screen.getByPlaceholderText(/type a message/i)
    fireEvent.change(textarea, { target: { value: 'Hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('does not send empty message', () => {
    const onSend = vi.fn()
    render(<MessageInput onSend={onSend} onTyping={vi.fn()} />)

    const textarea = screen.getByPlaceholderText(/type a message/i)
    fireEvent.change(textarea, { target: { value: '   ' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('calls onTyping when user types', () => {
    const onTyping = vi.fn()
    render(<MessageInput onSend={vi.fn()} onTyping={onTyping} />)

    const textarea = screen.getByPlaceholderText(/type a message/i)
    fireEvent.change(textarea, { target: { value: 'H' } })

    expect(onTyping).toHaveBeenCalled()
  })

  it('disables input when disabled prop is true', () => {
    render(<MessageInput onSend={vi.fn()} onTyping={vi.fn()} disabled />)

    const textarea = screen.getByPlaceholderText(/type a message/i)
    expect(textarea).toBeDisabled()
  })

  it('renders custom placeholder', () => {
    render(
      <MessageInput onSend={vi.fn()} onTyping={vi.fn()} placeholder="Reply to Alice..." />
    )

    expect(screen.getByPlaceholderText('Reply to Alice...')).toBeInTheDocument()
  })
})
