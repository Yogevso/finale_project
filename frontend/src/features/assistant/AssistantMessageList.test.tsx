import { render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import AssistantMessageList from './AssistantMessageList'

const baseProps = {
  messages: [],
  streamingText: '',
  isLoading: false,
  isStreaming: false,
  thinkingStatus: '',
  activeToolCalls: [],
  toolResults: new Map(),
}

describe('AssistantMessageList', () => {
  beforeAll(() => {
    HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  it('drops raw HTML and markdown images from assistant output', () => {
    render(
      <AssistantMessageList
        {...baseProps}
        messages={[
          {
            role: 'assistant',
            content:
              'Hello\n\n![](https://evil.test/track.png)\n\n<script>alert(1)</script>',
          },
        ]}
      />,
    )

    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    expect(document.querySelector('img')).toBeNull()
  })

  it('renders safe links and strips unsafe javascript links', () => {
    render(
      <AssistantMessageList
        {...baseProps}
        messages={[
          {
            role: 'assistant',
            content:
              '[Safe docs](https://example.com/docs) [Unsafe link](javascript:alert(1))',
          },
        ]}
      />,
    )

    expect(screen.getByRole('link', { name: 'Safe docs' })).toHaveAttribute(
      'href',
      'https://example.com/docs',
    )
    expect(screen.queryByRole('link', { name: 'Unsafe link' })).toBeNull()
    expect(screen.getByText('Unsafe link')).toBeInTheDocument()
  })

  it('applies the same sanitization rules to streaming assistant text', () => {
    render(
      <AssistantMessageList
        {...baseProps}
        streamingText={
          '<img src="https://evil.test/pixel.png" alt="pixel" /> [Mail me](mailto:test@example.com)'
        }
        isStreaming
      />,
    )

    expect(document.querySelector('img')).toBeNull()
    expect(screen.getByRole('link', { name: 'Mail me' })).toHaveAttribute(
      'href',
      'mailto:test@example.com',
    )
  })
})
