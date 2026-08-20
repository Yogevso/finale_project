import { createRef } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PreviewCanvas } from '@/pages/document-detail/components/PreviewCanvas'
import { PreviewToolbar } from '@/pages/document-detail/components/PreviewToolbar'
import { supportsFidelityView } from '@/pages/document-detail/hooks/useFidelityView'
import type { Attachment } from '@/types'

function buildAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 8,
    document_id: 40,
    filename: 'spec.pdf',
    original_filename: 'spec.pdf',
    file_size: 1024,
    mime_type: 'application/pdf',
    uploaded_by: 1,
    uploaded_at: '2026-08-20T00:00:00Z',
    ...overrides,
  }
}

function renderToolbar(props: Partial<Parameters<typeof PreviewToolbar>[0]> = {}) {
  const attachment = buildAttachment()
  render(
    <PreviewToolbar
      previewableAttachments={[attachment]}
      selectedAttachment={attachment}
      previewSource="reader"
      inlinePreviewAvailable
      onSelectAttachment={() => undefined}
      onSelectInlinePreview={() => undefined}
      readerError={null}
      onRetryReaderView={() => undefined}
      fontSize="default"
      onSetFontSize={() => undefined}
      theme="light"
      onSetTheme={() => undefined}
      {...props}
    />,
  )
}

function renderCanvas(props: Partial<Parameters<typeof PreviewCanvas>[0]> = {}) {
  render(
    <PreviewCanvas
      previewPaneRef={createRef<HTMLDivElement>()}
      documentPaperClass="document-preview-paper"
      activeHtmlContent="<p>structured text</p>"
      showingReaderView
      showDocumentTitle={false}
      searchTerm=""
      searchMatchCount={0}
      activeSearchMatchIndex={-1}
      onSearchTermChange={() => undefined}
      onPreviousSearchMatch={() => undefined}
      onNextSearchMatch={() => undefined}
      searchInputRef={createRef<HTMLInputElement>()}
      tocSectionsCount={0}
      readerCurrentPage={null}
      scrollProgress={0}
      sectionLinkBasePath="/documents/40"
      onScroll={() => undefined}
      hasUser={false}
      selectionPopup={{ show: false, x: 0, y: 0, text: '', anchorId: '' }}
      commentPopup={{ show: false, x: 0, y: 0, text: '', anchorId: '' }}
      commentText=""
      isPrivateComment={false}
      isSubmittingComment={false}
      onOpenCommentForm={() => undefined}
      onCloseCommentPopup={() => undefined}
      onCommentTextChange={() => undefined}
      onPrivateCommentChange={() => undefined}
      onSubmitComment={() => undefined}
      {...props}
    />,
  )
}

describe('supportsFidelityView', () => {
  it('accepts PDFs by mime type or extension', () => {
    expect(supportsFidelityView(buildAttachment())).toBe(true)
    expect(
      supportsFidelityView(
        buildAttachment({ mime_type: 'application/octet-stream', original_filename: 'Spec.PDF' }),
      ),
    ).toBe(true)
  })

  it('rejects everything else', () => {
    expect(supportsFidelityView(null)).toBe(false)
    expect(
      supportsFidelityView(
        buildAttachment({
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          filename: 'spec.docx',
          original_filename: 'spec.docx',
        }),
      ),
    ).toBe(false)
  })
})

describe('Original layout toggle', () => {
  it('is offered alongside the existing sources and reports the selection', async () => {
    const onSelectFidelityView = vi.fn()
    renderToolbar({ fidelityAvailable: true, onSelectFidelityView })

    expect(screen.getByRole('button', { name: 'Show current version content' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show source file preview' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Show the original page layout' }))
    expect(onSelectFidelityView).toHaveBeenCalledTimes(1)
  })

  it('is hidden when the attachment is not a PDF', () => {
    renderToolbar({ fidelityAvailable: false })

    expect(screen.queryByRole('button', { name: 'Show the original page layout' })).toBeNull()
  })

  it('does not steal the active state from Source file while inactive', () => {
    renderToolbar({ fidelityAvailable: true, showingFidelity: false })

    expect(screen.getByRole('button', { name: 'Show source file preview' }).className).toContain(
      'bg-sky-600',
    )
  })
})

describe('Fidelity rendering', () => {
  it('renders the layout in a fully sandboxed frame rather than the sanitized path', () => {
    const html = '<style>.pdf-fidelity{background:#f1f5f9}</style><div class="pdf-fidelity"></div>'
    renderCanvas({ showingFidelity: true, fidelityHtml: html })

    const frame = screen.getByTestId('document-fidelity-frame')
    expect(frame.getAttribute('sandbox')).toBe('')
    expect(frame.getAttribute('srcdoc')).toBe(html)
    // The normal, sanitized paper must not render at the same time.
    expect(screen.queryByTestId('document-preview-paper')).toBeNull()
  })

  it('surfaces the backend error instead of an empty frame', () => {
    renderCanvas({
      showingFidelity: true,
      fidelityHtml: null,
      fidelityError: 'Fidelity view is only available for PDF attachments',
    })

    expect(screen.queryByTestId('document-fidelity-frame')).toBeNull()
    expect(
      screen.getByText('Fidelity view is only available for PDF attachments'),
    ).toBeInTheDocument()
  })

  it('leaves the sanitized path untouched when the toggle is off', () => {
    renderCanvas({ showingFidelity: false })

    expect(screen.getByTestId('document-preview-paper')).toBeInTheDocument()
    expect(screen.queryByTestId('document-fidelity-frame')).toBeNull()
  })
})
