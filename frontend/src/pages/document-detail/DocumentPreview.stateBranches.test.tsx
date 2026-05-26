import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useEffect, useRef } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import type { Attachment } from '@/types'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { DocumentPreview } from './DocumentPreview'

const useReaderViewMock = vi.fn()
const useContentEditingFlowMock = vi.fn()
const downloadAttachmentMock = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getVersions: vi.fn(),
    getVersion: vi.fn(),
    getAttachmentBlob: vi.fn(),
    getAttachmentDownloadUrl: vi.fn(() => '/download'),
    getDocumentProgress: vi.fn(),
  },
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({ user: null }),
}))

vi.mock('@/hooks/useAttachmentDownload', () => ({
  useAttachmentDownload: () => ({
    downloadAttachment: downloadAttachmentMock,
  }),
}))

vi.mock('@/pages/document-detail/hooks/useInlineComments', () => ({
  useInlineComments: () => ({
    selectionPopup: { show: false, x: 0, y: 0, text: '', anchorId: '' },
    commentPopup: { show: false, x: 0, y: 0, text: '', anchorId: '' },
    commentText: '',
    isPrivateComment: false,
    isSubmittingComment: false,
    setCommentText: vi.fn(),
    setIsPrivateComment: vi.fn(),
    handleMouseUp: vi.fn(),
    handleOpenCommentForm: vi.fn(),
    handleSubmitComment: vi.fn(),
    handleCloseCommentPopup: vi.fn(),
  }),
}))

vi.mock('@/pages/document-detail/hooks/useContentEditingFlow', () => ({
  useContentEditingFlow: (...args: unknown[]) => useContentEditingFlowMock(...args),
}))

vi.mock('@/pages/document-detail/hooks/useReaderView', () => ({
  useReaderView: (...args: unknown[]) => useReaderViewMock(...args),
}))

vi.mock('@/pages/document-detail/hooks/usePreviewProgress', () => ({
  usePreviewProgress: () => ({
    previewScrollProgress: 0,
    handleScroll: vi.fn(),
  }),
}))

vi.mock('@/pages/document-detail/hooks/usePreviewShortcuts', () => ({
  usePreviewShortcuts: vi.fn(),
}))

vi.mock('@/pages/document-detail/components/PreviewToolbar', () => ({
  PreviewToolbar: () => <div data-testid="preview-toolbar" />,
}))

vi.mock('@/pages/document-detail/components/TocPanel', () => ({
  TocPanel: ({ sections }: { sections: TocSection[] }) => (
    <div data-testid="toc-panel">
      {sections.map((section) => (
        <div key={section.id}>{section.text}</div>
      ))}
    </div>
  ),
}))

vi.mock('@/pages/document-detail/components/PreviewCanvas', () => ({
  PreviewCanvas: ({ activeHtmlContent }: { activeHtmlContent: string | null }) => (
    <div data-testid="preview-canvas">{activeHtmlContent}</div>
  ),
}))

vi.mock('@/pages/document-detail/components/ContentEditChooserPopup', () => ({
  ContentEditChooserPopup: () => null,
}))

vi.mock('@/pages/document-detail/components/SectionEditPopup', () => ({
  SectionEditPopup: () => null,
}))

const { api } = await import('@/lib/api')
const mockedApi = vi.mocked(api, true)

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

function buildAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 1,
    document_id: 42,
    filename: 'reader.docx',
    original_filename: 'reader.docx',
    file_size: 128,
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    reader_html_status: 'pending',
    ...overrides,
  }
}

function buildReaderViewState(overrides: Record<string, unknown> = {}) {
  return {
    readerHtmlContent: null,
    readerStatus: null,
    readerWarnings: [],
    readerConfidence: null,
    readerError: null,
    isReaderLoading: false,
    readerCurrentPage: null,
    activeHeading: null,
    setReaderCurrentPage: vi.fn(),
    setActiveHeading: vi.fn(),
    navigateReaderToSection: vi.fn(),
    handleRetryReaderView: vi.fn(),
    hasReaderSections: false,
    ...overrides,
  }
}

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })

  return { promise, resolve, reject }
}

describe('DocumentPreview state branches', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.getVersions.mockResolvedValue({ items: [] } as never)
    mockedApi.getVersion.mockResolvedValue(null as never)
    downloadAttachmentMock.mockResolvedValue(undefined)
    useReaderViewMock.mockReturnValue(buildReaderViewState())
    useContentEditingFlowMock.mockReturnValue({
      showContentEditChooser: false,
      editingSection: null,
      handleCloseContentEditChooser: vi.fn(),
      handleStartEditingSection: vi.fn(),
      handleEditFullDocument: vi.fn(),
      handleChooseEditSection: vi.fn(),
      handleChooseAddSection: vi.fn(),
      handleCloseSectionEdit: vi.fn(),
      handleBackToChooser: vi.fn(),
      handleSaveSection: vi.fn(),
    })
  })

  it('shows a loading spinner for previewable attachments while reader content is pending', async () => {
    useReaderViewMock.mockReturnValue(
      buildReaderViewState({
        readerStatus: 'pending',
      }),
    )

    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[buildAttachment()]}
        documentTitle="Reader Document"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/preparing document preview/i)).toBeInTheDocument()
    })
  })

  it('shows the reader failure state when extraction fails for a selected attachment', async () => {
    useReaderViewMock.mockReturnValue(
      buildReaderViewState({
        readerStatus: 'failed',
        readerError: 'Reader extraction failed',
      }),
    )

    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[buildAttachment()]}
        documentTitle="Broken Reader"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Preview unavailable')).toBeInTheDocument()
    })

    expect(screen.getByText('Reader extraction failed')).toBeInTheDocument()
  })

  it('renders ready reader content and downloads the selected attachment from the footer action', async () => {
    const attachment = buildAttachment({
      id: 5,
      filename: 'guide.docx',
      original_filename: 'guide.docx',
      reader_html_status: 'ready',
    })

    useReaderViewMock.mockReturnValue(
      buildReaderViewState({
        readerHtmlContent: '<h1>Reader body</h1>',
        readerStatus: 'ready',
        readerConfidence: 0.97,
      }),
    )

    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[attachment]}
        documentTitle="Guide"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('preview-canvas')).toHaveTextContent('<h1>Reader body</h1>')
    })

    fireEvent.click(screen.getByRole('button', { name: 'Download Original' }))

    expect(downloadAttachmentMock).toHaveBeenCalledWith(attachment)
  })

  it('surfaces inline preview load failures inside the preview stage', async () => {
    mockedApi.getVersions.mockRejectedValue(new Error('network down'))
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    useReaderViewMock.mockReturnValue(
      buildReaderViewState({
        readerStatus: 'pending',
      }),
    )

    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[buildAttachment()]}
        documentTitle="Reader Document"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Failed to load preview')).toBeInTheDocument()
    })

    consoleErrorSpy.mockRestore()
  })

  it('does not let a stale inline load overwrite reader toc sections after attachment selection', async () => {
    const inlineResponse = createDeferred<{ items: Array<{ id: number; content: string; created_at: string; is_published: boolean }> }>()
    const attachment = buildAttachment({
      id: 9,
      filename: 'reentry.docx',
      original_filename: 'reentry.docx',
      reader_html_status: 'ready',
    })

    mockedApi.getVersions
      .mockImplementationOnce(() => inlineResponse.promise as never)
      .mockResolvedValue({ items: [] } as never)

    useReaderViewMock.mockImplementation(
      ({ selectedAttachment, setSections }: { selectedAttachment: Attachment | null; setSections: (value: TocSection[]) => void }) => {
        useEffect(() => {
          if (!selectedAttachment) {
            return
          }

          setSections([
            {
              id: 'reader-0',
              text: 'Program Overview',
              level: 1,
              html: '<h1>Program Overview</h1>',
              index: 0,
              anchorId: 'heading-reader-0',
            },
            {
              id: 'reader-1',
              text: 'Overview Notes',
              level: 2,
              html: '<h2>Overview Notes</h2>',
              index: 1,
              anchorId: 'heading-reader-1',
            },
          ])
        }, [selectedAttachment, setSections])

        return buildReaderViewState({
          readerHtmlContent: selectedAttachment ? '<h1>Reader body</h1>' : null,
          readerStatus: selectedAttachment ? 'ready' : null,
        })
      },
    )

    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[attachment]}
        documentTitle="Re-entry Document"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Overview Notes')).toBeInTheDocument()
    })

    inlineResponse.resolve({
      items: [
        {
          id: 101,
          content: '<h1>Inline Intro</h1><h2>Reference Appendix</h2>',
          created_at: '2026-01-01T00:00:00Z',
          is_published: true,
        },
      ],
    })

    await waitFor(() => {
      expect(screen.getByText('Overview Notes')).toBeInTheDocument()
    })

    expect(screen.queryByText('Inline Intro')).not.toBeInTheDocument()
    expect(screen.queryByText('Reference Appendix')).not.toBeInTheDocument()
  })

  it('keeps matched outline items after inline save while dropping stale entries', async () => {
    const attachment = buildAttachment({
      id: 11,
      filename: 'edited.docx',
      original_filename: 'edited.docx',
      reader_html_status: 'ready',
    })

    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 201,
          content: '<h1>Inline Intro</h1><h2>Reference Appendix</h2>',
          created_at: '2026-01-01T00:00:00Z',
          is_published: true,
        },
      ],
    } as never)

    useReaderViewMock.mockImplementation(
      ({ selectedAttachment, setSections }: { selectedAttachment: Attachment | null; setSections: (value: TocSection[]) => void }) => {
        useEffect(() => {
          if (!selectedAttachment) {
            return
          }

          setSections([
            {
              id: 'reader-0',
              text: 'Program Overview',
              level: 1,
              html: '<h1>Program Overview</h1>',
              index: 0,
              anchorId: 'heading-reader-0',
            },
            {
              id: 'reader-1',
              text: 'Overview Notes',
              level: 2,
              html: '',
              index: 1,
              anchorId: 'page-2',
            },
            {
              id: 'reader-2',
              text: 'Obsolete Section',
              level: 2,
              html: '',
              index: 2,
              anchorId: 'page-3',
            },
            {
              id: 'reader-3',
              text: 'Reference Appendix',
              level: 2,
              html: '<h2>Reference Appendix</h2>',
              index: 3,
              anchorId: 'heading-reader-3',
            },
          ])
        }, [selectedAttachment, setSections])

        return buildReaderViewState({
          readerHtmlContent: selectedAttachment ? '<h1>Reader body</h1>' : null,
          readerStatus: selectedAttachment ? 'ready' : null,
        })
      },
    )

    useContentEditingFlowMock.mockImplementation(
      ({
        sections,
        applyProcessedHtml,
      }: {
        sections: TocSection[]
        applyProcessedHtml: (html: string) => void
      }) => {
        const armedRef = useRef(false)
        const savedRef = useRef(false)

        useEffect(() => {
          if (!sections.some((section) => section.text === 'Overview Notes')) {
            return
          }

          if (!armedRef.current) {
            armedRef.current = true
            return
          }

          if (!savedRef.current) {
            savedRef.current = true
            applyProcessedHtml(
              '<article class="docx-document"><h1>Inline Intro</h1><p><strong>Overview Notes</strong></p><p>Body</p><h2>Reference Appendix</h2></article>',
            )
          }
        }, [applyProcessedHtml, sections])

        return {
          showContentEditChooser: false,
          editingSection: null,
          handleCloseContentEditChooser: vi.fn(),
          handleStartEditingSection: vi.fn(),
          handleEditFullDocument: vi.fn(),
          handleChooseEditSection: vi.fn(),
          handleChooseAddSection: vi.fn(),
          handleCloseSectionEdit: vi.fn(),
          handleBackToChooser: vi.fn(),
          handleSaveSection: vi.fn(),
        }
      },
    )

    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[attachment]}
        documentTitle="Edited Reader Document"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Overview Notes')).toBeInTheDocument()
    })

    expect(screen.getByText('Reference Appendix')).toBeInTheDocument()
    expect(screen.queryByText('Obsolete Section')).not.toBeInTheDocument()
  })
})
