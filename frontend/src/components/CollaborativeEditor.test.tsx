import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CollaborativeEditor } from './CollaborativeEditor'

vi.mock('@tiptap/react', async () => {
  const React = await import('react')

  return {
    EditorContent: ({ className }: { className?: string }) =>
      React.createElement('div', {
        className,
        'data-testid': 'editor-content',
      }),
    useEditor: () => ({
      commands: {
        setContent: vi.fn(() => true),
      },
      getHTML: () => '',
      setEditable: vi.fn(),
      chain: () => ({
        focus: () => ({
          toggleBold: () => ({ run: () => true }),
        }),
      }),
      isActive: () => false,
    }),
  }
})

vi.mock('@tiptap/starter-kit', () => ({
  default: {
    configure: () => ({}),
  },
}))

vi.mock('@tiptap/extension-underline', () => ({
  default: {},
}))

vi.mock('@tiptap/extension-text-align', () => ({
  default: {
    configure: () => ({}),
  },
}))

vi.mock('@tiptap/extension-table', () => ({
  Table: {
    configure: () => ({}),
  },
}))

vi.mock('@tiptap/extension-table-row', () => ({
  TableRow: {},
}))

vi.mock('@tiptap/extension-table-header', () => ({
  TableHeader: {},
}))

vi.mock('@tiptap/extension-table-cell', () => ({
  TableCell: {},
}))

vi.mock('@tiptap/extension-collaboration', () => ({
  default: {
    configure: () => ({}),
  },
}))

vi.mock('@tiptap/extension-collaboration-cursor', () => ({
  default: {
    configure: () => ({}),
  },
}))

describe('CollaborativeEditor', () => {
  it('shows a persistence failure banner and retries when requested', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <CollaborativeEditor
        ydoc={null}
        provider={null}
        isConnected={true}
        isConnecting={false}
        isSynced={true}
        error={null}
        persistenceWarning="Changes are no longer being saved to the server. Keep this tab open and reconnect before closing it."
        collaborators={[]}
        currentUser={{
          userId: 1,
          username: 'tester',
          color: '#2563eb',
        }}
        editable={false}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Server saving failed')
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Changes are no longer being saved to the server.',
    )

    await user.click(screen.getByRole('button', { name: 'Reconnect' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
