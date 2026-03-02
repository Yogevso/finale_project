import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useLocation, useNavigate, useParams, type NavigateFunction } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import {
  useDocumentDetailPageBundleQuery,
} from '@/hooks/useDocumentQueries'
import { queryKeys } from '@/lib/queryKeys'
import { setReadingWidth } from '@/lib/readingWidth'
import { useDocumentDetailPageState } from '@/pages/document-detail/hooks/useDocumentDetailPageState'
import { buildDocumentDetailCollaborationScenario } from '@/test/scenarios/documentDetailScenario'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useLocation: vi.fn(),
    useNavigate: vi.fn(),
    useParams: vi.fn(),
  }
})

vi.mock('@/lib/auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('@/hooks/useDocumentQueries', () => ({
  useDocumentDetailPageBundleQuery: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
  api: {
    assignCompanies: vi.fn(),
    deleteDocument: vi.fn(),
    removeCompanyAssignment: vi.fn(),
    submitForReview: vi.fn(),
    updateDocument: vi.fn(),
  },
}))

vi.mock('@/lib/readingWidth', () => ({
  getReadingWidth: vi.fn(() => 'reading'),
  setReadingWidth: vi.fn(),
}))

const mockedApi = vi.mocked(api, true)
const mockedUseParams = vi.mocked(useParams)
const mockedUseNavigate = vi.mocked(useNavigate)
const mockedUseLocation = vi.mocked(useLocation)
const mockedUseAuth = vi.mocked(useAuth)
const mockedUseDocumentDetailPageBundleQuery = vi.mocked(useDocumentDetailPageBundleQuery)
const mockedSetReadingWidth = vi.mocked(setReadingWidth)

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

describe('useDocumentDetailPageState', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const scenario = buildDocumentDetailCollaborationScenario(42)

    mockedUseParams.mockReturnValue({ id: '42' } as never)
    mockedUseNavigate.mockReturnValue(vi.fn() as unknown as NavigateFunction)
    mockedUseLocation.mockReturnValue({ pathname: '/documents/42', search: '' } as never)

    mockedUseAuth.mockReturnValue({ isEditor: true, isManager: true } as never)

    mockedUseDocumentDetailPageBundleQuery.mockReturnValue({
      data: scenario.bundle,
      isLoading: false,
      error: null,
    } as never)

    mockedApi.updateDocument.mockResolvedValue(scenario.bundle.document as never)
    mockedApi.deleteDocument.mockResolvedValue({ message: 'ok' } as never)
    mockedApi.assignCompanies.mockResolvedValue({ message: 'ok' } as never)
    mockedApi.removeCompanyAssignment.mockResolvedValue({ message: 'ok' } as never)
    mockedApi.submitForReview.mockResolvedValue({ id: 9 } as never)
  })

  it('routes edit action correctly between details editing and content editing', () => {
    const queryClient = createQueryClient()
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDocumentDetailPageState(), { wrapper })

    expect(result.current.activeTab).toBe('preview')
    expect(result.current.isEditing).toBe(false)

    act(() => {
      result.current.setActiveTab('details')
    })
    act(() => {
      result.current.handleEditAction()
    })
    expect(result.current.isEditing).toBe(true)

    act(() => {
      result.current.handleEditAction()
    })
    expect(result.current.isEditing).toBe(false)

    const previousToken = result.current.contentEditRequestToken
    act(() => {
      result.current.setActiveTab('versions')
    })
    act(() => {
      result.current.handleEditAction()
    })

    expect(result.current.activeTab).toBe('preview')
    expect(result.current.isEditing).toBe(false)
    expect(result.current.contentEditRequestToken).toBe(previousToken + 1)
  })

  it('persists width preference via reading-width helper and exposes fullscreen mode', () => {
    mockedUseLocation.mockReturnValue({
      pathname: '/documents/42/fullscreen',
      search: '?fullscreen=1',
    } as never)

    const queryClient = createQueryClient()
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDocumentDetailPageState(), { wrapper })

    expect(result.current.isFullscreen).toBe(true)
    expect(result.current.contentWidth).toBe('reading')

    act(() => {
      result.current.applyWidth('fluid')
    })

    expect(mockedSetReadingWidth).toHaveBeenCalledWith('fluid')
    expect(result.current.contentWidth).toBe('fluid')
    expect(result.current.contentWidthClass).toBe('max-w-none')
  })

  it('submits review, resets modal state, and invalidates related queries', async () => {
    const queryClient = createQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDocumentDetailPageState(), { wrapper })

    act(() => {
      result.current.openSubmitReview()
      result.current.setSubmitMessage('Please review section updates.')
    })

    expect(result.current.showSubmitReview).toBe(true)
    expect(result.current.submitMessage).toBe('Please review section updates.')

    act(() => {
      result.current.submitReview()
    })

    await waitFor(() => {
      expect(mockedApi.submitForReview).toHaveBeenCalledWith(42, {
        message: 'Please review section updates.',
      })
    })

    await waitFor(() => {
      expect(result.current.showSubmitReview).toBe(false)
      expect(result.current.submitMessage).toBe('')
    })

    const invalidatedKeys = invalidateSpy.mock.calls
      .map(([args]) => args?.queryKey)
      .filter((value) => value !== undefined)

    expect(invalidatedKeys).toEqual(
      expect.arrayContaining([
        queryKeys.bff.documentDetailBundle('42'),
        queryKeys.documents.detail('42'),
        queryKeys.reviews.all,
      ]),
    )
  })

  it('shows corrective guidance when company visibility update lacks assignments', async () => {
    const queryClient = createQueryClient()
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    mockedApi.updateDocument.mockRejectedValue({
      response: {
        data: {
          detail: 'Company visibility requires at least one assigned company',
          error_code: 'missing_company_assignment',
        },
      },
    } as never)

    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const { result } = renderHook(() => useDocumentDetailPageState(), { wrapper })

    act(() => {
      result.current.updateDocument({ visibility: 'company' })
    })

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(
        'Company visibility requires at least one assigned company. Use "Assign Companies" in Details first.',
      )
    })

    alertSpy.mockRestore()
  })

  it('blocks empty assignment save before mutation for company-visible documents', () => {
    const scenario = buildDocumentDetailCollaborationScenario(42)
    mockedUseDocumentDetailPageBundleQuery.mockReturnValue({
      data: {
        ...scenario.bundle,
        document: {
          ...scenario.bundle.document,
          visibility: 'company',
        },
      },
      isLoading: false,
      error: null,
    } as never)

    const queryClient = createQueryClient()
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    const { result } = renderHook(() => useDocumentDetailPageState(), { wrapper })

    act(() => {
      result.current.setActiveTab('details')
    })
    act(() => {
      result.current.toggleCompanySelector()
    })
    act(() => {
      result.current.updateAssignmentDraft([])
    })
    act(() => {
      result.current.saveAssignmentDraft()
    })

    expect(alertSpy).toHaveBeenCalledWith(
      'Company-visible documents must keep at least one assigned company.',
    )
    expect(mockedApi.assignCompanies).not.toHaveBeenCalled()

    alertSpy.mockRestore()
  })

  it('guards tab change when assignment draft has unsaved changes', () => {
    const queryClient = createQueryClient()
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    const { result } = renderHook(() => useDocumentDetailPageState(), { wrapper })

    act(() => {
      result.current.setActiveTab('details')
    })
    act(() => {
      result.current.toggleCompanySelector()
    })
    act(() => {
      result.current.updateAssignmentDraft([999])
    })
    act(() => {
      result.current.setActiveTab('preview')
    })

    expect(result.current.activeTab).toBe('details')
    expect(result.current.hasUnsavedAssignmentChanges).toBe(true)
    expect(confirmSpy).toHaveBeenCalledWith(
      'You have unsaved company assignment changes. Discard them?',
    )

    confirmSpy.mockRestore()
  })
})
