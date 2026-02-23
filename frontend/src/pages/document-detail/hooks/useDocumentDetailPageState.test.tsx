import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useLocation, useNavigate, useParams, type NavigateFunction } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import {
  useDocumentAssignedCompaniesQuery,
  useDocumentAttachmentsQuery,
  useDocumentDetailQuery,
  useDocumentReviewHistoryQuery,
} from '@/hooks/useDocumentQueries'
import { queryKeys } from '@/lib/queryKeys'
import { setReadingWidth } from '@/lib/readingWidth'
import { useDocumentDetailPageState } from '@/pages/document-detail/hooks/useDocumentDetailPageState'

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
  useDocumentAssignedCompaniesQuery: vi.fn(),
  useDocumentAttachmentsQuery: vi.fn(),
  useDocumentDetailQuery: vi.fn(),
  useDocumentReviewHistoryQuery: vi.fn(),
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
const mockedUseDocumentDetailQuery = vi.mocked(useDocumentDetailQuery)
const mockedUseDocumentAttachmentsQuery = vi.mocked(useDocumentAttachmentsQuery)
const mockedUseDocumentAssignedCompaniesQuery = vi.mocked(useDocumentAssignedCompaniesQuery)
const mockedUseDocumentReviewHistoryQuery = vi.mocked(useDocumentReviewHistoryQuery)
const mockedSetReadingWidth = vi.mocked(setReadingWidth)

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

const baseDocument = {
  id: 42,
  title: 'Safety Manual',
  document_number: 'DOC-42',
  description: 'Safety baseline',
  status: 'draft',
  visibility: 'internal',
  category: 'Ops',
  tags: null,
  created_by: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
}

describe('useDocumentDetailPageState', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    mockedUseParams.mockReturnValue({ id: '42' } as never)
    mockedUseNavigate.mockReturnValue(vi.fn() as unknown as NavigateFunction)
    mockedUseLocation.mockReturnValue({ pathname: '/documents/42', search: '' } as never)

    mockedUseAuth.mockReturnValue({ isEditor: true, isManager: true } as never)

    mockedUseDocumentDetailQuery.mockReturnValue({
      data: baseDocument,
      isLoading: false,
      error: null,
    } as never)
    mockedUseDocumentAttachmentsQuery.mockReturnValue({ data: [] } as never)
    mockedUseDocumentAssignedCompaniesQuery.mockReturnValue({ data: { companies: [] } } as never)
    mockedUseDocumentReviewHistoryQuery.mockReturnValue({ data: { items: [] } } as never)

    mockedApi.updateDocument.mockResolvedValue(baseDocument as never)
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
      expect.arrayContaining([queryKeys.documents.detail('42'), queryKeys.reviews.all]),
    )
  })
})
