import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { UploadDocumentModal } from './UploadDocumentModal'

const useUploadDocumentFlowMock = vi.fn()

vi.mock('@/components/CompanySelector', () => ({
  default: () => <div data-testid="company-selector" />,
}))

vi.mock('@/features/documents', () => ({
  applyAudiencePreset: vi.fn((value) => value),
  getAudienceDirtyHelperText: vi.fn(() => ({ isChanged: false, text: 'Audience unchanged' })),
  getAudienceVisibilityHelperText: vi.fn(() => 'Visible to internal users'),
  listAudiencePresets: vi.fn(() => []),
}))

vi.mock('@/pages/documents/hooks/useUploadDocumentFlow', () => ({
  ACCEPTED_FILE_TYPES: '.docx,.pptx,.pdf',
  MANAGER_UPLOAD_STATUS_OPTIONS: [
    { value: 'draft', label: 'Draft' },
    { value: 'approved', label: 'Approved' },
  ],
  useUploadDocumentFlow: (...args: unknown[]) => useUploadDocumentFlowMock(...args),
}))

function buildHookState(isPending: boolean, overrides: Record<string, unknown> = {}) {
  return {
    fileInputRef: { current: null },
    selectedFile: null,
    title: '',
    setTitle: vi.fn(),
    description: '',
    setDescription: vi.fn(),
    category: '',
    setCategory: vi.fn(),
    platform: '',
    setPlatform: vi.fn(),
    platformSuggestions: ['Meteor Lake'],
    releaseBranch: '',
    setReleaseBranch: vi.fn(),
    tags: '',
    setTags: vi.fn(),
    dueDate: '',
    setDueDate: vi.fn(),
    uploadStatus: 'draft',
    setUploadStatus: vi.fn(),
    visibility: 'internal' as const,
    setVisibility: vi.fn(),
    companyIds: [],
    setCompanyIds: vi.fn(),
    canManageAdvancedUploadOptions: false,
    contentFile: null,
    releaseNotesFile: null,
    selectedFileIsPdf: false,
    pdfConversionTarget: 'docx',
    setPdfConversionTarget: vi.fn(),
    error: '',
    setError: vi.fn(),
    dragActive: false,
    setDragActive: vi.fn(),
    uploadProgressPercent: isPending ? 48 : null,
    audienceDirtyState: {
      visibilityChanged: false,
      companyAssignmentsChanged: false,
    },
    uploadMutation: {
      isPending,
    },
    handleFileSelect: vi.fn(),
    handleSupplementalFileSelect: vi.fn(),
    handleDrop: vi.fn(),
    handleSubmit: vi.fn((event?: { preventDefault?: () => void }) => event?.preventDefault?.()),
    confirmClose: vi.fn(),
    ...overrides,
  }
}

describe('UploadDocumentModal', () => {
  it('disables cancel while an upload is in progress', () => {
    useUploadDocumentFlowMock.mockReturnValue(buildHookState(true))

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByText(/uploading\.\.\. please wait to close this window/i)).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: /upload progress/i })).toHaveAttribute(
      'aria-valuenow',
      '48',
    )
  })

  it('keeps cancel available when idle', () => {
    useUploadDocumentFlowMock.mockReturnValue(buildHookState(false))

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Cancel' })).not.toBeDisabled()
    expect(screen.queryByText(/please wait to close this window/i)).not.toBeInTheDocument()
  })

  it('shows manager upload extras when advanced options are available', () => {
    useUploadDocumentFlowMock.mockReturnValue(
      buildHookState(false, {
        canManageAdvancedUploadOptions: true,
        contentFile: { name: 'appendix.docx' },
        releaseNotesFile: { name: 'release-notes.pptx' },
      }),
    )

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByText(/manager upload options/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/initial status/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/additional content file/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/release notes file/i)).toBeInTheDocument()
    expect(screen.getByText('appendix.docx')).toBeInTheDocument()
    expect(screen.getByText('release-notes.pptx')).toBeInTheDocument()
  })

  it('replaces placeholder dropzone text with icons and descriptive copy', () => {
    useUploadDocumentFlowMock.mockReturnValue(buildHookState(false))

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByText(/upload docx, pptx, or pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/platform/i)).toBeInTheDocument()
    expect(screen.queryByText(/^FILE$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^UP$/)).not.toBeInTheDocument()
  })

  it('shows PDF conversion options when the selected file is a PDF', () => {
    useUploadDocumentFlowMock.mockReturnValue(
      buildHookState(false, {
        selectedFileIsPdf: true,
        selectedFile: { name: 'legacy.pdf', size: 2_000_000 },
        pdfConversionTarget: 'pptx',
      }),
    )

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByText(/pdf conversion target/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/word \(.docx\)/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/powerpoint \(.pptx\)/i)).toBeChecked()
  })
})
