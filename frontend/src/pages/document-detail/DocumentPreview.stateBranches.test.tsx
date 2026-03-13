import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Attachment } from '@/types'
import { DocumentPreview } from './DocumentPreview'

const useReaderViewMock = vi.fn()
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
    selectionPopup: { show: false, x: 0, y: 0, text: '' },
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
  useContentEditingFlow: () => ({
    showContentEditChooser: false,
    editingSection: null,
    handleCloseContentEditChooser: vi.fn(),
    handleStartEditingSection: vi.fn(),
    handleChooseEditSection: vi.fn(),
    handleChooseAddSection: vi.fn(),
    handleCloseSectionEdit: vi.fn(),
    handleBackToChooser: vi.fn(),
    handleSaveSection: vi.fn(),
  }),
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
  TocPanel: () => <div data-testid="toc-panel" />,
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

describe('DocumentPreview state branches', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.getVersions.mockResolvedValue({ items: [] } as never)
    mockedApi.getVersion.mockResolvedValue(null as never)
    downloadAttachmentMock.mockResolvedValue(undefined)
    useReaderViewMock.mockReturnValue(buildReaderViewState())
  })

  it('shows a loading spinner for previewable attachments while reader content is pending', async () => {
    useReaderViewMock.mockReturnValue(
      buildReaderViewState({
        readerStatus: 'pending',
      }),
    )

    render(
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

    render(
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

    render(
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

    fireEvent.click(screen.getByRole('link', { name: 'Download Original' }))

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

    render(
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
})
