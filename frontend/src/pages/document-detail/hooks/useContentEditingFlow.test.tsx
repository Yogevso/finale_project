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
    getVersion: vi.fn(),
    getVersions: vi.fn(),
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
    const onRequireInlineContent = vi.fn()
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
          onRequireInlineContent,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.showContentEditChooser).toBe(true)
    })

    expect(onRequireInlineContent).not.toHaveBeenCalled()
  })

  it('requests a switch back to inline content when edit is triggered in reader view', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
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
          onRequireInlineContent,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(onRequireInlineContent).toHaveBeenCalledTimes(1)
    })

    expect(result.current.showContentEditChooser).toBe(false)
  })

  it('can open a full document editing target from the chooser flow', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
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
          activeHtmlContent: '<h2>Introduction</h2><p>Body</p><table><tbody><tr><td>Cell</td></tr></tbody></table>',
          isLoading: false,
          sections: baseSections,
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.showContentEditChooser).toBe(true)
    })

    act(() => {
      result.current.handleEditFullDocument()
    })

    expect(result.current.editingSection).toMatchObject({
      editMode: 'full',
      index: -1,
      text: 'Document Content',
    })
    expect(result.current.editingSection?.html).toContain('<table>')
  })

  it('falls back to full document editing when a chosen toc item has no standalone html block', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

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
          activeHtmlContent:
            '<h2>Status Summary</h2><p>Body</p><h2>Issue Notes</h2><div class="table-wrapper"><table><tbody><tr><td>Cell</td></tr></tbody></table></div>',
          isLoading: false,
          sections: [
            ...baseSections,
            {
              id: 'toc-acronyms',
              text: 'Reference Table',
              level: 2,
              html: '',
              index: 1,
              anchorId: 'page-3',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'toc-acronyms',
        text: 'Reference Table',
        level: 2,
        html: '',
        index: 1,
        anchorId: 'page-3',
      })
    })

    expect(result.current.editingSection).toMatchObject({
      editMode: 'full',
      index: -1,
      text: 'Reference Table',
    })
    expect(result.current.editingSection?.html).toContain('<table>')
  })

  it('builds a fragment edit target for outline-only toc items that map to a paragraph and table block', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

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
          activeHtmlContent:
            '<article class="docx-document">' +
            '<h2>Introduction</h2><p>Body</p>' +
            '<p><strong>Reference Table</strong></p>' +
            '<div class="table-wrapper"><table><tbody><tr><td>ABC</td><td>Alpha</td></tr></tbody></table></div>' +
            '<h2>Next Section</h2><p>Later body</p>' +
            '</article>',
          isLoading: false,
          sections: [
            ...baseSections,
            {
              id: 'toc-acronyms',
              text: 'Reference Table',
              level: 2,
              html: '',
              index: 1,
              anchorId: 'page-3',
            },
            {
              id: 'next-section',
              text: 'Next Section',
              level: 2,
              html: '<h2>Next Section</h2><p>Later body</p>',
              index: 2,
              anchorId: 'heading-2',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'toc-acronyms',
        text: 'Reference Table',
        level: 2,
        html: '',
        index: 1,
        anchorId: 'page-3',
      })
    })

    expect(result.current.editingSection).toMatchObject({
      editMode: 'edit',
      text: 'Reference Table',
      replaceStartIndex: 2,
      replaceNodeCount: 2,
    })
    expect(result.current.editingSection?.html).toContain('Reference Table')
    expect(result.current.editingSection?.html).toContain('<table>')
  })

  it('uses surrounding toc order to edit the later matching block when labels repeat', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

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
          activeHtmlContent:
            '<article class="docx-document">' +
            '<h2>Introduction</h2><p>Body</p>' +
            '<p><strong>Reference Table</strong></p><p>Front matter copy</p>' +
            '<h2>Main Section</h2><p>Section body</p>' +
            '<p><strong>Reference Table</strong></p>' +
            '<div class="table-wrapper"><table><tbody><tr><td>ABC</td><td>Body section table</td></tr></tbody></table></div>' +
            '<h2>Next Section</h2><p>Later body</p>' +
            '</article>',
          isLoading: false,
          sections: [
            ...baseSections,
            {
              id: 'main-section',
              text: 'Main Section',
              level: 2,
              html: '<h2>Main Section</h2><p>Section body</p>',
              index: 1,
              anchorId: 'heading-1',
            },
            {
              id: 'toc-acronyms',
              text: 'Reference Table',
              level: 2,
              html: '',
              index: 2,
              anchorId: 'page-3',
            },
            {
              id: 'next-section',
              text: 'Next Section',
              level: 2,
              html: '<h2>Next Section</h2><p>Later body</p>',
              index: 3,
              anchorId: 'heading-3',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'toc-acronyms',
        text: 'Reference Table',
        level: 2,
        html: '',
        index: 2,
        anchorId: 'page-3',
      })
    })

    expect(result.current.editingSection).toMatchObject({
      text: 'Reference Table',
      replaceStartIndex: 6,
      replaceNodeCount: 2,
    })
    expect(result.current.editingSection?.html).toContain('Body section table')
    expect(result.current.editingSection?.html).not.toContain('Front matter copy')
  })

  it('saves edited section, submits review, and invalidates related queries', async () => {
    const queryClient = createQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 70,
          content: '<h2>Introduction</h2><p>Body</p>',
          created_at: '2026-03-09T00:00:00.000Z',
          is_published: true,
          published_at: '2026-03-09T00:00:00.000Z',
        },
      ],
    } as never)
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
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection(baseSections[0])
    })

    await act(async () => {
      await result.current.handleSaveSection('<h2>Introduction</h2><p>New content</p>', true)
    })

    expect(applyProcessedHtml).toHaveBeenCalledWith(
      expect.stringContaining('<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>New content</p>'),
    )
    expect(mockedApi.createVersion).toHaveBeenCalledWith(
      42,
      expect.objectContaining({
        content: expect.stringContaining(
          '<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>New content</p>',
        ),
      }),
    )
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

  it('replaces only the matched fragment when saving an outline-derived edit target', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 70,
          content:
            '<article class="docx-document"><h2>Introduction</h2><p>Body</p><p><strong>Reference Table</strong></p><div class="table-wrapper"><table><tbody><tr><td>ABC</td><td>Alpha</td></tr></tbody></table></div><h2>Next Section</h2><p>Later body</p></article>',
          created_at: '2026-03-09T00:00:00.000Z',
          is_published: true,
          published_at: '2026-03-09T00:00:00.000Z',
        },
      ],
    } as never)
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
          activeHtmlContent:
            '<article class="docx-document">' +
            '<h2>Introduction</h2><p>Body</p>' +
            '<p><strong>Reference Table</strong></p>' +
            '<div class="table-wrapper"><table><tbody><tr><td>ABC</td><td>Alpha</td></tr></tbody></table></div>' +
            '<h2>Next Section</h2><p>Later body</p>' +
            '</article>',
          isLoading: false,
          sections: [
            ...baseSections,
            {
              id: 'toc-acronyms',
              text: 'Reference Table',
              level: 2,
              html: '',
              index: 1,
              anchorId: 'page-3',
            },
            {
              id: 'next-section',
              text: 'Next Section',
              level: 2,
              html: '<h2>Next Section</h2><p>Later body</p>',
              index: 2,
              anchorId: 'heading-2',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'toc-acronyms',
        text: 'Reference Table',
        level: 2,
        html: '',
        index: 1,
        anchorId: 'page-3',
      })
    })

    await act(async () => {
      await result.current.handleSaveSection(
        '<p><strong>Reference Table</strong></p><table><tbody><tr><td>XYZ</td><td>Updated</td></tr></tbody></table>',
        false,
      )
    })

    expect(applyProcessedHtml).toHaveBeenCalledWith(
      expect.stringContaining('<td>XYZ</td><td>Updated</td>'),
    )
    expect(applyProcessedHtml).toHaveBeenCalledWith(
      expect.stringContaining('<h2>Introduction</h2><p>Body</p>'),
    )
    expect(applyProcessedHtml).toHaveBeenCalledWith(
      expect.stringContaining('<h2>Next Section</h2><p>Later body</p>'),
    )
  })

  it('replaces the intended repeated-label fragment instead of the earliest match', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 70,
          content:
            '<article class="docx-document"><h2>Introduction</h2><p>Body</p><p><strong>Reference Table</strong></p><p>Front matter copy</p><h2>Main Section</h2><p>Section body</p><p><strong>Reference Table</strong></p><div class="table-wrapper"><table><tbody><tr><td>ABC</td><td>Body section table</td></tr></tbody></table></div><h2>Next Section</h2><p>Later body</p></article>',
          created_at: '2026-03-09T00:00:00.000Z',
          is_published: true,
          published_at: '2026-03-09T00:00:00.000Z',
        },
      ],
    } as never)
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
          activeHtmlContent:
            '<article class="docx-document">' +
            '<h2>Introduction</h2><p>Body</p>' +
            '<p><strong>Reference Table</strong></p><p>Front matter copy</p>' +
            '<h2>Main Section</h2><p>Section body</p>' +
            '<p><strong>Reference Table</strong></p>' +
            '<div class="table-wrapper"><table><tbody><tr><td>ABC</td><td>Body section table</td></tr></tbody></table></div>' +
            '<h2>Next Section</h2><p>Later body</p>' +
            '</article>',
          isLoading: false,
          sections: [
            ...baseSections,
            {
              id: 'main-section',
              text: 'Main Section',
              level: 2,
              html: '<h2>Main Section</h2><p>Section body</p>',
              index: 1,
              anchorId: 'heading-1',
            },
            {
              id: 'toc-acronyms',
              text: 'Reference Table',
              level: 2,
              html: '',
              index: 2,
              anchorId: 'page-3',
            },
            {
              id: 'next-section',
              text: 'Next Section',
              level: 2,
              html: '<h2>Next Section</h2><p>Later body</p>',
              index: 3,
              anchorId: 'heading-3',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'toc-acronyms',
        text: 'Reference Table',
        level: 2,
        html: '',
        index: 2,
        anchorId: 'page-3',
      })
    })

    await act(async () => {
      await result.current.handleSaveSection(
        '<p><strong>Reference Table</strong></p><table><tbody><tr><td>XYZ</td><td>Updated body section table</td></tr></tbody></table>',
        false,
      )
    })

    expect(applyProcessedHtml).toHaveBeenCalledWith(
      expect.stringContaining('<p>Front matter copy</p>'),
    )
    expect(applyProcessedHtml).toHaveBeenCalledWith(
      expect.stringContaining('<td>XYZ</td><td>Updated body section table</td>'),
    )
  })

  it('preserves the section anchor id when edited heading html drops the id attribute', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 70,
          content:
            '<article class="docx-document"><h2 id="heading-0">Introduction</h2><p>Body</p></article>',
          created_at: '2026-03-09T00:00:00.000Z',
          is_published: true,
          published_at: '2026-03-09T00:00:00.000Z',
        },
      ],
    } as never)
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
          activeHtmlContent:
            '<article class="docx-document"><h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body</p></article>',
          isLoading: false,
          sections: [
            {
              id: 'section-1',
              text: 'Introduction',
              level: 2,
              html: '<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body</p>',
              index: 0,
              anchorId: 'heading-0',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'section-1',
        text: 'Introduction',
        level: 2,
        html: '<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body</p>',
        index: 0,
        anchorId: 'heading-0',
      })
    })

    await act(async () => {
      await result.current.handleSaveSection('<h2>Introduction Updated</h2><p>Body updated</p>', false)
    })

    const createVersionPayload = mockedApi.createVersion.mock.calls[0]?.[1] as
      | { content?: string }
      | undefined
    expect(createVersionPayload?.content).toContain('id="heading-0"')
    expect(applyProcessedHtml).toHaveBeenCalledWith(expect.stringContaining('id="heading-0"'))
  })

  it('assigns a unique heading id for inserted sections and keeps toc anchors unique', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 70,
          content:
            '<article class="docx-document"><h2 id="heading-0">Intro</h2><p>Body</p><h2 id="heading-1">Next</h2><p>Tail</p></article>',
          created_at: '2026-03-09T00:00:00.000Z',
          is_published: true,
          published_at: '2026-03-09T00:00:00.000Z',
        },
      ],
    } as never)
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
          activeHtmlContent:
            '<article class="docx-document"><h2 id="heading-0" class="scroll-mt-4">Intro</h2><p>Body</p><h2 id="heading-1" class="scroll-mt-4">Next</h2><p>Tail</p></article>',
          isLoading: false,
          sections: [
            {
              id: 'section-1',
              text: 'Intro',
              level: 2,
              html: '<h2 id="heading-0" class="scroll-mt-4">Intro</h2><p>Body</p>',
              index: 0,
              anchorId: 'heading-0',
            },
            {
              id: 'section-2',
              text: 'Next',
              level: 2,
              html: '<h2 id="heading-1" class="scroll-mt-4">Next</h2><p>Tail</p>',
              index: 1,
              anchorId: 'heading-1',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseAddSection(0)
    })

    await act(async () => {
      await result.current.handleSaveSection('<h2>bellow 1</h2><p>Inserted body</p>', false)
    })

    const createVersionPayload = mockedApi.createVersion.mock.calls[0]?.[1] as
      | { content?: string }
      | undefined
    const headingIds = Array.from(
      (createVersionPayload?.content || '').matchAll(/<h[1-6][^>]*id=\"([^\"]+)\"/g),
    ).map((match) => match[1])

    expect(headingIds).toContain('heading-0')
    expect(headingIds).toContain('heading-1')
    expect(new Set(headingIds).size).toBe(headingIds.length)
  })

  it('does not raise a false conflict when current processed html matches the latest raw document content', async () => {
    const queryClient = createQueryClient()
    const onRequireInlineContent = vi.fn()
    const applyProcessedHtml = vi.fn()

    mockedApi.createVersion.mockResolvedValue({ id: 77 } as never)
    mockedApi.getVersions.mockResolvedValue({
      items: [
        {
          id: 70,
          content: '<article class="docx-document"><h2>Introduction</h2><p>Body</p></article>',
          created_at: '2026-03-09T00:00:00.000Z',
          is_published: true,
          published_at: '2026-03-09T00:00:00.000Z',
        },
      ],
    } as never)
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
          activeHtmlContent:
            '<article class="docx-document"><h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body</p></article>',
          isLoading: false,
          sections: [
            {
              id: 'section-1',
              text: 'Introduction',
              level: 2,
              html: '<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body</p>',
              index: 0,
              anchorId: 'heading-0',
            },
          ],
          applyProcessedHtml,
          onRequireInlineContent,
        }),
      { wrapper },
    )

    act(() => {
      result.current.handleChooseEditSection({
        id: 'section-1',
        text: 'Introduction',
        level: 2,
        html: '<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body</p>',
        index: 0,
        anchorId: 'heading-0',
      })
    })

    let saveResult
    await act(async () => {
      saveResult = await result.current.handleSaveSection(
        '<h2 id="heading-0" class="scroll-mt-4">Introduction</h2><p>Body updated</p>',
        false,
      )
    })

    expect(saveResult).toEqual({ status: 'saved' })
    expect(mockedApi.createVersion).toHaveBeenCalled()
  })
})
