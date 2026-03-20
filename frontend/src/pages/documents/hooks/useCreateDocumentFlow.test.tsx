import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { loadCustomDocumentTemplates } from '@/lib/documentTemplates'
import { useCreateDocumentFlow } from './useCreateDocumentFlow'

const navigateMock = vi.fn()
const toastSuccessMock = vi.fn()
const toastErrorMock = vi.fn()
const createDraftDocumentMock = vi.fn()
const loadDuplicateDocumentDraftMock = vi.fn()
const listDocumentsMock = vi.fn()
const getDefaultAudienceForRoleMock = vi.fn()
const getAudienceDirtyStateMock = vi.fn()
const validateAudienceFormPayloadMock = vi.fn()
const checkDocumentDuplicatesMock = vi.fn()
const extractApiErrorMessageMock = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('@/features/documents', () => ({
  documentsUseCases: {
    createDraftDocument: (...args: unknown[]) => createDraftDocumentMock(...args),
    loadDuplicateDocumentDraft: (...args: unknown[]) => loadDuplicateDocumentDraftMock(...args),
    listDocuments: (...args: unknown[]) => listDocumentsMock(...args),
  },
  getDefaultAudienceForRole: (...args: unknown[]) => getDefaultAudienceForRoleMock(...args),
  getAudienceDirtyState: (...args: unknown[]) => getAudienceDirtyStateMock(...args),
  validateAudienceFormPayload: (...args: unknown[]) => validateAudienceFormPayloadMock(...args),
}))

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      role: 'admin',
    },
  }),
}))

vi.mock('@/lib/toast', () => ({
  useToast: () => ({
    success: toastSuccessMock,
    error: toastErrorMock,
  }),
  extractApiErrorMessage: (...args: unknown[]) => extractApiErrorMessageMock(...args),
}))

vi.mock('@/lib/api', () => ({
  api: {
    checkDocumentDuplicates: (...args: unknown[]) => checkDocumentDuplicatesMock(...args),
  },
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

describe('useCreateDocumentFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    getDefaultAudienceForRoleMock.mockReturnValue('internal')
    getAudienceDirtyStateMock.mockReturnValue({
      visibilityChanged: false,
      companyAssignmentsChanged: false,
    })
    validateAudienceFormPayloadMock.mockReturnValue(null)
    checkDocumentDuplicatesMock.mockResolvedValue({ has_matches: false, matches: [] })
    listDocumentsMock.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      pages: 1,
    })
    createDraftDocumentMock.mockResolvedValue({ id: 321 })
    loadDuplicateDocumentDraftMock.mockResolvedValue({
      title: 'Copy of Source Document',
      description: 'Copied body',
      platform: 'Core Platform',
      category: 'Guides',
      tags: 'copy',
      content: '<p>Copied</p>',
      parent_id: 44,
      visibility: 'internal',
      company_ids: [],
      release_branch: '',
      due_date: '',
      topic: '',
    })
    extractApiErrorMessageMock.mockImplementation((_error, fallback) => fallback)
  })

  it('can save a local template without creating a document', async () => {
    const onClose = vi.fn()
    const { wrapper, invalidateQueriesMock } = createWrapper()
    const { result } = renderHook(() => useCreateDocumentFlow({ onClose }), { wrapper })

    act(() => {
      result.current.setFormData((previous) => ({
        ...previous,
        title: 'Operations Guide',
        description: 'Reusable guide for operations',
        category: 'Operations',
        tags: 'ops, guide',
        content: '<h1>Operations Guide</h1><p>Checklist</p>',
      }))
      result.current.setSaveAsTemplate(true)
      result.current.setTemplateName('Operations Guide Template')
      result.current.setTemplateDescription('Reusable guide template')
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith(
        'Template saved',
        'Added to your personal Template Library.',
      )
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    expect(createDraftDocumentMock).not.toHaveBeenCalled()
    expect(invalidateQueriesMock).not.toHaveBeenCalled()
    expect(navigateMock).not.toHaveBeenCalled()
    expect(loadCustomDocumentTemplates()).toEqual([
      expect.objectContaining({
        name: 'Operations Guide Template',
        description: 'Reusable guide template',
        category: 'Operations',
        tags: ['ops', 'guide'],
        content: '<h1>Operations Guide</h1><p>Checklist</p>',
        source: 'custom',
      }),
    ])
  })

  it('creates a document and navigates to the editor in normal mode', async () => {
    const onClose = vi.fn()
    const { wrapper, invalidateQueriesMock } = createWrapper()
    const { result } = renderHook(() => useCreateDocumentFlow({ onClose }), { wrapper })

    act(() => {
      result.current.setFormData((previous) => ({
        ...previous,
        title: 'Normal Draft',
        platform: 'Core Platform',
        content: '<p>Body</p>',
      }))
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    await waitFor(() => {
      expect(createDraftDocumentMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Normal Draft',
          content: '<p>Body</p>',
        }),
        { generateWord: false },
      )
    })

    await waitFor(() => {
      expect(invalidateQueriesMock).toHaveBeenCalled()
      expect(toastSuccessMock).toHaveBeenCalledWith('Document created', 'Opening the editor...')
      expect(onClose).toHaveBeenCalledTimes(1)
      expect(navigateMock).toHaveBeenCalledWith('/documents/321/fullscreen')
    })
  })

  it('prefills the form from an existing document copy source', async () => {
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCreateDocumentFlow({ onClose }), { wrapper })

    await act(async () => {
      await result.current.handleCopyFromDocument({
        id: 44,
        title: 'Source Document',
        document_number: 'DOC-44',
      })
    })

    expect(loadDuplicateDocumentDraftMock).toHaveBeenCalledWith(44)
    expect(result.current.formData).toEqual(
      expect.objectContaining({
        title: 'Copy of Source Document',
        description: 'Copied body',
        platform: 'Core Platform',
        category: 'Guides',
        tags: 'copy',
        content: '<p>Copied</p>',
        parent_id: 44,
      }),
    )
    expect(result.current.selectedSourceDocument).toEqual({
      id: 44,
      title: 'Source Document',
      document_number: 'DOC-44',
    })
  })

  it('blocks document creation when title is missing', () => {
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCreateDocumentFlow({ onClose }), { wrapper })

    act(() => {
      result.current.setFormData((previous) => ({
        ...previous,
        platform: 'Core Platform',
      }))
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    expect(result.current.fieldErrors.title).toBe('Title is required')
    expect(result.current.error).toBe('')
    expect(createDraftDocumentMock).not.toHaveBeenCalled()
  })

  it('blocks document creation when platform is missing', () => {
    const onClose = vi.fn()
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCreateDocumentFlow({ onClose }), { wrapper })

    act(() => {
      result.current.setFormData((previous) => ({
        ...previous,
        title: 'No Platform Draft',
      }))
    })

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() } as never)
    })

    expect(result.current.fieldErrors.platform).toBe('Platform is required')
    expect(result.current.error).toBe('')
    expect(createDraftDocumentMock).not.toHaveBeenCalled()
  })
})
