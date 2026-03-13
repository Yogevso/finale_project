import { useMemo, useRef, useState, type CSSProperties } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PreviewCanvas } from '@/pages/document-detail/components/PreviewCanvas'
import { PreviewToolbar } from '@/pages/document-detail/components/PreviewToolbar'
import {
  DOCUMENT_FONT_SIZE_VALUES,
  getDocumentFontSize,
  getDocumentTheme,
  getDocumentThemeClassName,
  setDocumentFontSize,
  setDocumentTheme,
  type DocumentFontSize,
  type DocumentTheme,
} from '@/lib/documentReadingPreferences'

const clipboardWriteTextMock = vi.fn()

function ReadingUXHarness({ scrollProgress = 37 }: { scrollProgress?: number }) {
  const [fontSize, setFontSizeState] = useState<DocumentFontSize>(() => getDocumentFontSize())
  const [theme, setThemeState] = useState<DocumentTheme>(() => getDocumentTheme())
  const previewPaneRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  const handleSetFontSize = (value: DocumentFontSize) => {
    setFontSizeState(value)
    setDocumentFontSize(value)
  }

  const handleSetTheme = (value: DocumentTheme) => {
    setThemeState(value)
    setDocumentTheme(value)
  }

  const contentStyle = useMemo(
    () =>
      ({
        '--doc-font-size': DOCUMENT_FONT_SIZE_VALUES[fontSize],
      }) as CSSProperties,
    [fontSize],
  )

  return (
    <MemoryRouter>
      <div className="document-preview-shell surface-card rounded-2xl overflow-hidden">
        <PreviewToolbar
          previewableAttachments={[]}
          selectedAttachment={null}
          onSelectAttachment={() => undefined}
          readerError={null}
          onRetryReaderView={() => undefined}
          fontSize={fontSize}
          onSetFontSize={handleSetFontSize}
          theme={theme}
          onSetTheme={handleSetTheme}
        />
        <PreviewCanvas
          previewPaneRef={previewPaneRef}
          documentPaperClass={`document-preview-paper ${getDocumentThemeClassName(theme)}`}
          activeHtmlContent={'<h2 id="intro">Introduction</h2><p>Body copy</p>'}
          showingReaderView={false}
          showDocumentTitle={false}
          searchTerm=""
          searchMatchCount={0}
          activeSearchMatchIndex={-1}
          extractionWarnings={[]}
          readerConfidence={null}
          onSearchTermChange={() => undefined}
          onPreviousSearchMatch={() => undefined}
          onNextSearchMatch={() => undefined}
          searchInputRef={searchInputRef}
          tocSectionsCount={1}
          readerCurrentPage={null}
          commentPopupTopOffset={0}
          scrollProgress={scrollProgress}
          contentStyle={contentStyle}
          sectionLinkBasePath="/documents/42"
          onScroll={() => undefined}
          onMouseUp={() => undefined}
          hasUser={false}
          selectionPopup={{ show: false, x: 0, y: 0, text: '' }}
          commentPopup={{ show: false, x: 0, y: 0, text: '', anchorId: '' }}
          commentText=""
          isPrivateComment={false}
          isSubmittingComment={false}
          onOpenCommentForm={() => undefined}
          onCloseCommentPopup={() => undefined}
          onCommentTextChange={() => undefined}
          onPrivateCommentChange={() => undefined}
          onSubmitComment={() => undefined}
        />
      </div>
    </MemoryRouter>
  )
}

describe('ReadingUX controls', () => {
  beforeEach(() => {
    localStorage.clear()
    clipboardWriteTextMock.mockReset()
    clipboardWriteTextMock.mockResolvedValue(undefined)
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: clipboardWriteTextMock,
      },
    })
  })

  it('persists font size across remounts', async () => {
    const user = userEvent.setup()
    const firstRender = render(<ReadingUXHarness />)

    await user.click(screen.getByRole('button', { name: /set large font size/i }))
    expect(document.getElementById('document-content-area')).toHaveStyle('--doc-font-size: 1.15rem')

    firstRender.unmount()
    render(<ReadingUXHarness />)

    expect(document.getElementById('document-content-area')).toHaveStyle('--doc-font-size: 1.15rem')
  })

  it('applies the selected theme class to the paper for all three modes', async () => {
    const user = userEvent.setup()
    render(<ReadingUXHarness />)

    const paper = screen.getByTestId('document-preview-paper')

    await user.click(screen.getByRole('button', { name: /use sepia theme/i }))
    expect(paper).toHaveClass('document-preview-paper--sepia')

    await user.click(screen.getByRole('button', { name: /use dark theme/i }))
    expect(paper).toHaveClass('document-preview-paper--dark')

    await user.click(screen.getByRole('button', { name: /use light theme/i }))
    expect(paper).toHaveClass('document-preview-paper--light')
  })

  it('matches the reading progress bar width to the scroll percentage', () => {
    render(<ReadingUXHarness scrollProgress={64} />)

    expect(screen.getByTestId('document-reading-progress-bar')).toHaveStyle({ width: '64%' })
  })

  it('copies heading anchor links with the document URL', async () => {
    render(<ReadingUXHarness />)

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /copy link to intro/i }))
      await Promise.resolve()
    })

    const expectedUrl = new URL('/documents/42#intro', window.location.origin).toString()
    expect(clipboardWriteTextMock).toHaveBeenCalledWith(expectedUrl)
  })

  it('shows an extraction warning banner when reader warnings are present', () => {
    const previewPaneRef = { current: null }
    const searchInputRef = { current: null }

    render(
      <MemoryRouter>
        <PreviewCanvas
          previewPaneRef={previewPaneRef}
          documentPaperClass="document-preview-paper document-preview-paper--light"
          activeHtmlContent={'<article class="docx-document"><p>Body copy</p></article>'}
          showingReaderView
          showDocumentTitle={false}
          searchTerm=""
          searchMatchCount={0}
          activeSearchMatchIndex={-1}
          extractionWarnings={[{ code: 'MISSING_IMAGES', message: '1 images failed', count: 1 }]}
          readerConfidence={0.91}
          onSearchTermChange={() => undefined}
          onPreviousSearchMatch={() => undefined}
          onNextSearchMatch={() => undefined}
          searchInputRef={searchInputRef}
          tocSectionsCount={0}
          readerCurrentPage={1}
          commentPopupTopOffset={0}
          scrollProgress={0}
          sectionLinkBasePath="/documents/42"
          onScroll={() => undefined}
          onMouseUp={() => undefined}
          hasUser={false}
          selectionPopup={{ show: false, x: 0, y: 0, text: '' }}
          commentPopup={{ show: false, x: 0, y: 0, text: '', anchorId: '' }}
          commentText=""
          isPrivateComment={false}
          isSubmittingComment={false}
          onOpenCommentForm={() => undefined}
          onCloseCommentPopup={() => undefined}
          onCommentTextChange={() => undefined}
          onPrivateCommentChange={() => undefined}
          onSubmitComment={() => undefined}
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(/some document elements were only partially extracted/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(
      '1 images failed Extraction confidence: 91%.',
    )
  })
})
