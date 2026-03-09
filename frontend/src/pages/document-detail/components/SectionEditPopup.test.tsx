import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { saveDraftRecovery } from '@/lib/draftRecovery'
import { SectionEditPopup } from '@/pages/document-detail/components/SectionEditPopup'
import type { SectionEditTarget } from '@/pages/document-detail/helpers/previewHelpers'
import type { SectionSaveResult } from '@/pages/document-detail/hooks/useContentEditingFlow'

type UpdateHandler = () => void

type CommandChain = {
  focus: () => CommandChain
  toggleBold: () => CommandChain
  toggleItalic: () => CommandChain
  toggleUnderline: () => CommandChain
  toggleHeading: (_options?: { level: number }) => CommandChain
  toggleBulletList: () => CommandChain
  toggleOrderedList: () => CommandChain
  run: () => boolean
}

type MockEditor = {
  html: string
  getHTML: () => string
  commands: {
    setContent: (nextHtml: string) => boolean
  }
  on: (_event: string, handler: UpdateHandler) => void
  off: (_event: string, handler: UpdateHandler) => void
  chain: () => CommandChain
  isActive: (_name: string, _options?: Record<string, unknown>) => boolean
}

function buildCommandChain(): CommandChain {
  return {
    focus: () => buildCommandChain(),
    toggleBold: () => buildCommandChain(),
    toggleItalic: () => buildCommandChain(),
    toggleUnderline: () => buildCommandChain(),
    toggleHeading: () => buildCommandChain(),
    toggleBulletList: () => buildCommandChain(),
    toggleOrderedList: () => buildCommandChain(),
    run: () => true,
  }
}

vi.mock('@tiptap/react', async () => {
  const React = await import('react')

  return {
    EditorContent: ({
      editor,
      className,
    }: {
      editor: MockEditor | null
      className?: string
    }) =>
      React.createElement(
        'div',
        { className },
        React.createElement('div', {
          className: 'ProseMirror',
          contentEditable: true,
          suppressContentEditableWarning: true,
          dangerouslySetInnerHTML: { __html: editor?.html ?? '' },
        }),
      ),
    useEditor: ({ content }: { content: string }) => {
      const [html, setHtml] = React.useState(content)
      const handlersRef = React.useRef<Set<UpdateHandler>>(new Set())

      React.useEffect(() => {
        setHtml(content)
      }, [content])

      return React.useMemo<MockEditor>(
        () => ({
          html,
          getHTML: () => html,
          commands: {
            setContent: (nextHtml: string) => {
              setHtml(nextHtml)
              handlersRef.current.forEach((handler) => handler())
              return true
            },
          },
          on: (_event: string, handler: UpdateHandler) => {
            handlersRef.current.add(handler)
          },
          off: (_event: string, handler: UpdateHandler) => {
            handlersRef.current.delete(handler)
          },
          chain: () => buildCommandChain(),
          isActive: () => false,
        }),
        [html],
      )
    },
  }
})

const baseSection: SectionEditTarget = {
  id: 'intro',
  text: 'Introduction',
  level: 2,
  html: '<h2>Introduction</h2><p>Original body</p>',
  index: 0,
  anchorId: 'intro',
  editMode: 'edit',
}

describe('DraftRecovery in SectionEditPopup', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('shows a stored draft notice and restores the saved draft into the editor', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(
      async (
        _newHtml: string,
        _submitForReview: boolean,
        _options?: { force?: boolean; comparisonHtml?: string },
      ): Promise<SectionSaveResult> => ({ status: 'saved' }),
    )

    saveDraftRecovery(
      {
        documentId: 42,
        sectionId: baseSection.id,
        editMode: baseSection.editMode,
      },
      {
        html: '<h2>Introduction</h2><p>Recovered draft copy</p>',
        baseHtml: baseSection.html,
        savedAt: '2026-03-09T10:00:00.000Z',
      },
    )

    render(
      <SectionEditPopup
        documentId={42}
        section={baseSection}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    )

    expect(await screen.findByText(/restore unsaved changes/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /restore draft/i }))

    await waitFor(() => {
      expect(document.querySelector('.ProseMirror')).toHaveTextContent('Recovered draft copy')
    })
    expect(document.querySelector('.ProseMirror')).not.toHaveTextContent('Original body')
  })
})
