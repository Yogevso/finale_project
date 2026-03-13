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
  ACCEPTED_FILE_TYPES: '.docx,.pptx',
  useUploadDocumentFlow: (...args: unknown[]) => useUploadDocumentFlowMock(...args),
}))

function buildHookState(isPending: boolean) {
  return {
    fileInputRef: { current: null },
    selectedFile: null,
    title: '',
    setTitle: vi.fn(),
    description: '',
    setDescription: vi.fn(),
    category: '',
    setCategory: vi.fn(),
    releaseBranch: '',
    setReleaseBranch: vi.fn(),
    tags: '',
    setTags: vi.fn(),
    dueDate: '',
    setDueDate: vi.fn(),
    visibility: 'internal' as const,
    setVisibility: vi.fn(),
    companyIds: [],
    setCompanyIds: vi.fn(),
    error: '',
    setError: vi.fn(),
    dragActive: false,
    setDragActive: vi.fn(),
    audienceDirtyState: {
      visibilityChanged: false,
      companyAssignmentsChanged: false,
    },
    uploadMutation: {
      isPending,
    },
    handleFileSelect: vi.fn(),
    handleDrop: vi.fn(),
    handleSubmit: vi.fn((event?: { preventDefault?: () => void }) => event?.preventDefault?.()),
    confirmClose: vi.fn(),
  }
}

describe('UploadDocumentModal', () => {
  it('disables cancel while an upload is in progress', () => {
    useUploadDocumentFlowMock.mockReturnValue(buildHookState(true))

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByText(/uploading\.\.\. please wait to close this window/i)).toBeInTheDocument()
  })

  it('keeps cancel available when idle', () => {
    useUploadDocumentFlowMock.mockReturnValue(buildHookState(false))

    render(<UploadDocumentModal onClose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Cancel' })).not.toBeDisabled()
    expect(screen.queryByText(/please wait to close this window/i)).not.toBeInTheDocument()
  })
})
