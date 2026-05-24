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
  insertTable: (_options: { rows: number; cols: number; withHeaderRow: boolean }) => CommandChain
  addRowAfter: () => CommandChain
  addColumnAfter: () => CommandChain
  deleteRow: () => CommandChain
  deleteColumn: () => CommandChain
  deleteTable: () => CommandChain
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

const commandSpies = {
  insertTable: vi.fn(),
  addRowAfter: vi.fn(),
  addColumnAfter: vi.fn(),
  deleteRow: vi.fn(),
  deleteColumn: vi.fn(),
  deleteTable: vi.fn(),
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
    insertTable: (options) => {
      commandSpies.insertTable(options)
      return buildCommandChain()
    },
    addRowAfter: () => {
      commandSpies.addRowAfter()
      return buildCommandChain()
    },
    addColumnAfter: () => {
      commandSpies.addColumnAfter()
      return buildCommandChain()
    },
    deleteRow: () => {
      commandSpies.deleteRow()
      return buildCommandChain()
    },
    deleteColumn: () => {
      commandSpies.deleteColumn()
      return buildCommandChain()
    },
    deleteTable: () => {
      commandSpies.deleteTable()
      return buildCommandChain()
    },
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
    Object.values(commandSpies).forEach((spy) => spy.mockReset())
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
    expect(screen.getByTestId('local-autosave-status')).toHaveTextContent('Auto-saved locally at')

    await user.click(screen.getByRole('button', { name: /restore draft/i }))

    await waitFor(() => {
      expect(document.querySelector('.ProseMirror')).toHaveTextContent('Recovered draft copy')
    })
    expect(document.querySelector('.ProseMirror')).not.toHaveTextContent('Original body')
  })

  it('warns the browser before unload when a local draft exists', async () => {
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
        onSave={vi.fn(async (): Promise<SectionSaveResult> => ({ status: 'saved' }))}
      />,
    )

    await screen.findByText(/restore unsaved changes/i)

    const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent
    Object.defineProperty(event, 'returnValue', {
      configurable: true,
      writable: true,
      value: undefined,
    })

    window.dispatchEvent(event)

    expect(event.returnValue).toBe('')
  })

  it('shows full document and table controls for complex editing', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(
      async (
        _newHtml: string,
        _submitForReview: boolean,
        _options?: { force?: boolean; comparisonHtml?: string },
      ): Promise<SectionSaveResult> => ({ status: 'saved' }),
    )

    render(
      <SectionEditPopup
        documentId={42}
        section={{
          ...baseSection,
          editMode: 'full',
          index: -1,
          text: 'Document Content',
          html:
            '<article class="docx-document"><h2>Introduction</h2><div class="table-wrapper">' +
            '<table><tbody><tr><td>Cell</td></tr></tbody></table>' +
            '</div></article>',
        }}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    )

    expect(screen.getByText(/including tables and mixed layout blocks/i)).toBeInTheDocument()
    expect(document.querySelector('.ProseMirror table')).not.toBeNull()
    expect(document.querySelector('.ProseMirror .table-wrapper')).toBeNull()
    expect(document.querySelector('.ProseMirror article')).toBeNull()

    await user.click(screen.getByRole('button', { name: /insert table/i }))
    await user.click(screen.getByRole('button', { name: /add table row/i }))
    await user.click(screen.getByRole('button', { name: /add table column/i }))

    expect(commandSpies.insertTable).toHaveBeenCalledWith({
      rows: 3,
      cols: 3,
      withHeaderRow: true,
    })
    expect(commandSpies.addRowAfter).toHaveBeenCalledTimes(1)
    expect(commandSpies.addColumnAfter).toHaveBeenCalledTimes(1)

    // Check the "Submit for review" checkbox to change the button text
    await user.click(screen.getByRole('checkbox', { name: /submit for review after saving/i }))
    await user.click(screen.getByRole('button', { name: /save & submit for review/i }))

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.stringContaining('<article class="docx-document">'),
        true,
      )
    })
    expect(onSave).toHaveBeenCalledWith(
      expect.not.stringContaining('table-wrapper'),
      true,
    )
  })

  it('auto-resolves concurrent edits without rendering the conflict panel', async () => {
    const user = userEvent.setup()
    const onSave = vi
      .fn<
        [string, boolean, ({ force?: boolean; comparisonHtml?: string } | undefined)?],
        Promise<SectionSaveResult>
      >()
      .mockResolvedValueOnce({
        status: 'conflict',
        draftDocumentHtml: '<h2>Introduction</h2><p>Draft copy</p>',
        liveDocumentHtml: '<h2>Introduction</h2><p>Live copy</p>',
        liveEditorHtml: '<h2>Introduction</h2><p>Live copy</p>',
      })
      .mockResolvedValueOnce({ status: 'saved' })

    const onClose = vi.fn()

    render(
      <SectionEditPopup
        documentId={42}
        section={baseSection}
        onClose={onClose}
        onSave={onSave}
      />,
    )

    await user.click(screen.getByRole('button', { name: /save as draft/i }))

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledTimes(2)
    })
    expect(onSave).toHaveBeenNthCalledWith(
      2,
      expect.any(String),
      false,
      expect.objectContaining({
        force: true,
        comparisonHtml: '<h2>Introduction</h2><p>Live copy</p>',
      }),
    )
    expect(screen.queryByText(/concurrent edits detected/i)).not.toBeInTheDocument()
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows a professional conflict message when a pending review blocks saving', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(
      async (): Promise<SectionSaveResult> => {
        throw {
          response: {
            status: 409,
            data: {
              detail: 'Cannot create a new version while a review is pending',
            },
          },
        }
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

    await user.click(screen.getByRole('button', { name: /save as draft/i }))

    expect(
      await screen.findByText(
        'Cannot save while this document has a pending review. ' +
          'Ask a manager/admin to resolve the current review, then try again.',
      ),
    ).toBeInTheDocument()
  })

  it('disables save actions and explains why when saving is blocked by pending review', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(
      async (
        _newHtml: string,
        _submitForReview: boolean,
        _options?: { force?: boolean; comparisonHtml?: string },
      ): Promise<SectionSaveResult> => ({ status: 'saved' }),
    )

    render(
      <SectionEditPopup
        documentId={42}
        section={baseSection}
        onClose={vi.fn()}
        onSave={onSave}
        saveDisabled
      />,
    )

    const saveButton = screen.getByRole('button', { name: /save as draft/i })
    expect(saveButton).toBeDisabled()
    expect(
      screen.getByText(/this document has a pending review\. resolve it before creating a new draft\./i),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open reviews/i })).toHaveAttribute('href', '/reviews')

    await user.click(saveButton)
    expect(onSave).not.toHaveBeenCalled()
  })
})
