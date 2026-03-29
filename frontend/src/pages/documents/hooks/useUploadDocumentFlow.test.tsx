import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DOCUMENT_INPUT_LIMITS } from '@/lib/uiInputRules'
import { useUploadDocumentFlow } from './useUploadDocumentFlow'

const navigateMock = vi.fn()
const toastSuccessMock = vi.fn()
const toastErrorMock = vi.fn()
const validateDocumentUploadFileMock = vi.fn()
const validateAudienceFormPayloadMock = vi.fn()
const getAudienceDirtyStateMock = vi.fn()
const getDefaultAudienceForRoleMock = vi.fn()
const uploadDocumentMock = vi.fn()
const listDocumentsMock = vi.fn()
const extractApiErrorMessageMock = vi.fn()
const authState = {
  user: {
    id: 1,
    role: 'admin',
  },
  isManager: true,
}

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('@/features/documents', () => ({
  DOCUMENT_UPLOAD_ACCEPTED_FILE_TYPES: '.docx,.pptx,.pdf',
  documentsUseCases: {
    listDocuments: (...args: unknown[]) => listDocumentsMock(...args),
    uploadDocument: (...args: unknown[]) => uploadDocumentMock(...args),
  },
  getDefaultAudienceForRole: (...args: unknown[]) => getDefaultAudienceForRoleMock(...args),
  getAudienceDirtyState: (...args: unknown[]) => getAudienceDirtyStateMock(...args),
  validateAudienceFormPayload: (...args: unknown[]) => validateAudienceFormPayloadMock(...args),
  validateDocumentUploadFile: (...args: unknown[]) => validateDocumentUploadFileMock(...args),
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => authState,
}))

vi.mock('@/lib/toast', () => ({
  useToast: () => ({
    success: toastSuccessMock,
    error: toastErrorMock,
  }),
  extractApiErrorMessage: (...args: unknown[]) => extractApiErrorMessageMock(...args),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const invalidateQueriesMock = vi
    .spyOn(queryClient, 'invalidateQueries')
    .mockResolvedValue(undefined as never)

  return {
    invalidateQueriesMock,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  }
}

describe('useUploadDocumentFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authState.user = {
      id: 1,
      role: 'admin',
    }
    authState.isManager = true
    getDefaultAudienceForRoleMock.mockReturnValue('internal')
    getAudienceDirtyStateMock.mockImplementation(
      (_baseline, current) => ({
        visibilityChanged: current.visibility !== 'internal',
        companyAssignmentsChanged: (current.company_ids || []).length > 0,
      }),
    )
    validateDocumentUploadFileMock.mockReturnValue(null)
    validateAudienceFormPayloadMock.mockReturnValue(null)
    listDocumentsMock.mockResolvedValue({
      items: [{ id: 1, title: 'Seed Doc', document_number: 'DOC-1', platform: 'Meteor Lake' }],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    })
    uploadDocumentMock.mockResolvedValue({ id: 123 })
    extractApiErrorMessageMock.mockImplementation((_err, fallback) => fallback)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('rejects invalid files before they are selected', () => {
    validateDocumentUploadFileMock.mockReturnValue('Only DOCX, PPTX, and PDF files are allowed')
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose: vi.fn() }), { wrapper })

    act(() => {
      result.current.handleFileSelect(
        new File(['pdf'], 'bad.pdf', { type: 'application/pdf' }),
      )
    })

    expect(result.current.selectedFile).toBeNull()
    expect(result.current.error).toBe('Only DOCX, PPTX, and PDF files are allowed')
  })

  it('requires a file before submitting', () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose: vi.fn() }), { wrapper })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    expect(result.current.error).toBe('Please select a file to upload')
  })

  it('requires a platform before submitting', () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose: vi.fn() }), { wrapper })

    act(() => {
      result.current.handleFileSelect(
        new File(['docx'], 'guide.docx', {
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }),
      )
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    expect(result.current.error).toBe('Platform is required')
    expect(uploadDocumentMock).not.toHaveBeenCalled()
  })

  it('confirms before closing when unsaved changes exist', () => {
    const onClose = vi.fn()
    const confirmMock = vi.fn(() => false)
    vi.stubGlobal('confirm', confirmMock)
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })

    act(() => {
      result.current.handleFileSelect(
        new File(['docx'], 'guide.docx', {
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }),
      )
    })

    act(() => {
      result.current.confirmClose()
    })

    expect(confirmMock).toHaveBeenCalledWith('You have unsaved changes. Discard them?')
    expect(onClose).not.toHaveBeenCalled()

    confirmMock.mockReturnValue(true)
    act(() => {
      result.current.confirmClose()
    })

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('uploads a valid file, invalidates document queries, and navigates to fullscreen', async () => {
    const onClose = vi.fn()
    const { wrapper, invalidateQueriesMock } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })
    const file = new File(['docx'], 'guide.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    act(() => {
      result.current.handleFileSelect(file)
      result.current.setPlatform('Meteor Lake')
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(uploadDocumentMock).toHaveBeenCalledWith(file, {
        title: 'guide',
        description: '',
        category: '',
        platform: 'Meteor Lake',
        releaseBranch: '',
        tags: '',
        dueDate: '',
        status: 'draft',
        visibility: 'internal',
        companyIds: [],
        contentFile: null,
        releaseNotesFile: null,
      }, expect.objectContaining({
        onUploadProgress: expect.any(Function),
      }))
    })

    await waitFor(() => {
      expect(invalidateQueriesMock).toHaveBeenCalled()
      expect(toastSuccessMock).toHaveBeenCalledWith('Document uploaded', 'Opening the document...')
      expect(onClose).toHaveBeenCalledTimes(1)
      expect(navigateMock).toHaveBeenCalledWith('/documents/123/fullscreen')
    })
  })

  it('normalizes upload metadata and falls back to the file stem when title is blank', async () => {
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })
    const file = new File(['docx'], 'release-notes-2026.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    act(() => {
      result.current.handleFileSelect(file)
      result.current.setTitle('   ')
      result.current.setDescription(' First line.  \n\n\nSecond line.   ')
      result.current.setCategory('  Reports  ')
      result.current.setPlatform('  Meteor   Lake  ')
      result.current.setReleaseBranch('  R580  ')
      result.current.setTags('ops, release, Ops')
      result.current.setDueDate(' 2026-04-01 ')
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(uploadDocumentMock).toHaveBeenCalledWith(file, {
        title: 'release-notes-2026',
        description: 'First line.\n\nSecond line.',
        category: 'Reports',
        platform: 'Meteor Lake',
        releaseBranch: 'R580',
        tags: 'ops, release',
        dueDate: '2026-04-01',
        status: 'draft',
        visibility: 'internal',
        companyIds: [],
        contentFile: null,
        releaseNotesFile: null,
      }, expect.objectContaining({
        onUploadProgress: expect.any(Function),
      }))
    })
  })

  it('truncates oversized upload titles to the documented limit', async () => {
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })
    const file = new File(['docx'], 'guide.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const oversizedTitle = ` ${'B'.repeat(DOCUMENT_INPUT_LIMITS.title + 20)} `

    act(() => {
      result.current.handleFileSelect(file)
      result.current.setTitle(oversizedTitle)
      result.current.setPlatform('Meteor Lake')
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(uploadDocumentMock).toHaveBeenCalledWith(file, expect.objectContaining({
        title: 'B'.repeat(DOCUMENT_INPUT_LIMITS.title),
      }), expect.objectContaining({
        onUploadProgress: expect.any(Function),
      }))
    })
  })

  it('surfaces upload errors through local state and toast feedback', async () => {
    uploadDocumentMock.mockRejectedValue(new Error('boom'))
    extractApiErrorMessageMock.mockReturnValue('Upload exploded')
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })

    act(() => {
      result.current.handleFileSelect(
        new File(['docx'], 'guide.docx', {
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }),
      )
      result.current.setPlatform('Meteor Lake')
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(result.current.error).toBe('Upload exploded')
    })

    expect(toastErrorMock).toHaveBeenCalledWith('Upload failed', 'Upload exploded')
    expect(onClose).not.toHaveBeenCalled()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('tracks upload progress and forwards manager-only upload metadata', async () => {
    let resolveUpload: ((value: { id: number }) => void) | undefined
    uploadDocumentMock.mockImplementation((_file, _metadata, options) => {
      options?.onUploadProgress?.({ loaded: 55, total: 100 } as never)
      return new Promise((resolve) => {
        resolveUpload = resolve
      })
    })

    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })
    const primaryFile = new File(['docx'], 'guide.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const contentFile = new File(['docx'], 'appendix.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const releaseNotesFile = new File(['pptx'], 'release-notes.pptx', {
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })

    act(() => {
      result.current.handleFileSelect(primaryFile)
      result.current.setPlatform('Meteor Lake')
      result.current.setUploadStatus('approved')
      result.current.handleSupplementalFileSelect('content', contentFile)
      result.current.handleSupplementalFileSelect('releaseNotes', releaseNotesFile)
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(result.current.uploadProgressPercent).toBe(55)
    })

    expect(uploadDocumentMock).toHaveBeenCalledWith(primaryFile, {
      title: 'guide',
      description: '',
      category: '',
      platform: 'Meteor Lake',
      releaseBranch: '',
      tags: '',
      dueDate: '',
      status: 'approved',
      visibility: 'internal',
      companyIds: [],
      contentFile,
      releaseNotesFile,
    }, expect.objectContaining({
      onUploadProgress: expect.any(Function),
    }))

    act(() => {
      resolveUpload?.({ id: 222 })
    })

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/documents/222/fullscreen')
    })
  })

  it('forwards the selected PDF conversion target for PDF uploads', async () => {
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose }), { wrapper })
    const primaryFile = new File(['pdf'], 'legacy.pdf', {
      type: 'application/pdf',
    })

    act(() => {
      result.current.handleFileSelect(primaryFile)
      result.current.setPlatform('Meteor Lake')
      result.current.setPdfConversionTarget('pptx')
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(uploadDocumentMock).toHaveBeenCalledWith(primaryFile, {
        title: 'legacy',
        description: '',
        category: '',
        platform: 'Meteor Lake',
        releaseBranch: '',
        tags: '',
        dueDate: '',
        status: 'draft',
        visibility: 'internal',
        companyIds: [],
        contentFile: null,
        releaseNotesFile: null,
        pdfConversionTarget: 'pptx',
      }, expect.objectContaining({
        onUploadProgress: expect.any(Function),
      }))
    })
  })

  it('rejects invalid supplemental files before upload', () => {
    validateDocumentUploadFileMock.mockImplementation((file: File) =>
      file.name.endsWith('.exe') ? 'Only DOCX, PPTX, and PDF files are allowed' : null,
    )
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose: vi.fn() }), { wrapper })

    act(() => {
      result.current.handleSupplementalFileSelect(
        'releaseNotes',
        new File(['exe'], 'notes.exe', { type: 'application/octet-stream' }),
      )
    })

    expect(result.current.releaseNotesFile).toBeNull()
    expect(result.current.error).toBe('Release notes file: Only DOCX, PPTX, and PDF files are allowed')
  })

  it('hides manager upload extras for non-manager editors', () => {
    authState.user = {
      id: 2,
      role: 'editor',
    }
    authState.isManager = false

    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useUploadDocumentFlow({ onClose: vi.fn() }), { wrapper })

    expect(result.current.canManageAdvancedUploadOptions).toBe(false)
    expect(result.current.uploadStatus).toBe('draft')
  })
})
