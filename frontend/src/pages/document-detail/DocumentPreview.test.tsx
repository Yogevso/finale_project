import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import type { Attachment } from '@/types'
import { DocumentPreview } from './DocumentPreview'

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
  useReaderView: () => ({
    readerHtmlContent: null,
    readerStatus: null,
    readerWarnings: [],
    readerConfidence: null,
    readerError: null,
    isReaderLoading: false,
    readerCurrentPage: null,
    activeHeading: null,
    showingReaderView: false,
    setReaderCurrentPage: vi.fn(),
    setActiveHeading: vi.fn(),
    navigateReaderToSection: vi.fn(),
    handleRetryReaderView: vi.fn(),
    hasReaderSections: false,
  }),
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
    filename: 'legacy.bin',
    original_filename: 'legacy.bin',
    file_size: 128,
    mime_type: 'application/octet-stream',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('DocumentPreview empty states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.getVersions.mockResolvedValue({ items: [] } as never)
    mockedApi.getVersion.mockResolvedValue(null as never)
  })

  it('shows download-only UI when attachments exist but none are previewable', async () => {
    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[buildAttachment()]}
        documentTitle="Legacy Attachment"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Preview Not Available' })).toBeInTheDocument()
    })

    expect(
      screen.getByText(/this attachment can be downloaded, but it cannot be previewed inline/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download legacy\.bin/i })).toBeInTheDocument()
  })

  it('shows no-content UI when there are no attachments and no inline content', async () => {
    renderWithQueryClient(
      <DocumentPreview
        documentId={42}
        attachments={[]}
        documentTitle="Empty Document"
        sectionLinkBasePath="/documents/42"
      />,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'No Content Yet' })).toBeInTheDocument()
    })

    expect(screen.queryByRole('heading', { name: 'Preview Not Available' })).not.toBeInTheDocument()
  })
})
