import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useContentEditingFlow } from '@/pages/document-detail/hooks/useContentEditingFlow'

vi.mock('@/lib/api', () => ({
  api: {
    createVersion: vi.fn(),
    getDocument: vi.fn(),
    updateDocument: vi.fn(),
    submitForReview: vi.fn(),
  },
}))

const mockedApi = vi.mocked(api, true)

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

const baseSections: TocSection[] = [
  {
    id: 'section-1',
    text: 'Introduction',
    level: 2,
    html: '<h2>Introduction</h2><p>Old content</p>',
    index: 0,
    anchorId: 'heading-0',
  },
]

describe('useContentEditingFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens chooser when edit request token is received for editable HTML content', async () => {
    const queryClient = createQueryClient()
    const onRequireOriginalPdf = vi.fn()
    const applyProcessedHtml = vi.fn()

    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(
      () =>
        useContentEditingFlow({
          documentId: 42,
          isEditor: true,
          contentEditRequestToken: 1,
          showingReaderView: false,
          activeHtmlContent: '<h2>Introduction</h2><p>Body</p>',
          isLoading: false,
          sections: baseSections,
          applyProcessedHtml,
          onRequireOriginalPdf,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.showContentEditChooser).toBe(true)
    })

    expect(onRequireOriginalPdf).not.toHaveBeenCalled()
  })

  it('requests switch back to original PDF when edit is triggered in reader view', async () => {
    const queryClient = createQueryClient()
    const onRequireOriginalPdf = vi.fn()
    const applyProcessedHtml = vi.fn()

    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(
      () =>
        useContentEditingFlow({
          documentId: 42,
          isEditor: true,
          contentEditRequestToken: 3,
          showingReaderView: true,
          activeHtmlContent: '<h2>Introduction</h2><p>Body</p>',
          isLoading: false,
          sections: baseSections,
          applyProcessedHtml,
          onRequireOriginalPdf,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(onRequireOriginalPdf).toHaveBeenCalledTimes(1)
    })

    expect(result.current.showContentEditChooser).toBe(false)
  })

  it('saves edited section, submits review, and invalidates related queries', async () => {
    const queryClient = createQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const onRequireOriginalPdf = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getDocument.mockResolvedValue({ id: 42, etag: 'doc-42-v2' } as never)
    mockedApi.updateDocument.mockResolvedValue({ id: 42, status: 'draft' } as never)
    mockedApi.submitForReview.mockResolvedValue({ id: 9 } as never)

    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(
      () =>
        useContentEditingFlow({
          documentId: 42,
          isEditor: true,
          contentEditRequestToken: 0,
          showingReaderView: false,
          activeHtmlContent: '<h2>Introduction</h2><p>Body</p>',
          isLoading: false,
          sections: baseSections,
          applyProcessedHtml,
          onRequireOriginalPdf,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection(baseSections[0])
    })

    await act(async () => {
      await result.current.handleSaveSection('<h2>Introduction</h2><p>New content</p>', true)
    })

    expect(applyProcessedHtml).toHaveBeenCalledWith('<h2>Introduction</h2><p>New content</p>')
    expect(mockedApi.createVersion).toHaveBeenCalledWith(
      42,
      expect.objectContaining({
        content: '<h2>Introduction</h2><p>New content</p>',
      }),
    )
    expect(mockedApi.updateDocument).toHaveBeenCalledWith(42, { status: 'draft' }, 'doc-42-v2')
    expect(mockedApi.submitForReview).toHaveBeenCalledWith(42, {
      version_id: 77,
      message: 'Edited section: "Introduction"',
    })

    const invalidatedKeys = invalidateSpy.mock.calls
      .map(([arg]) => arg?.queryKey)
      .filter((value) => value !== undefined)

    expect(invalidatedKeys).toEqual(
      expect.arrayContaining([
        queryKeys.documents.versions(42),
        queryKeys.documents.detail(42),
        queryKeys.reviews.all,
      ]),
    )
  })
})
