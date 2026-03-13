import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { usePreviewProgress } from './usePreviewProgress'

vi.mock('@/lib/api', () => ({
  api: {
    getDocumentProgress: vi.fn(),
  },
}))

const mockedApi = vi.mocked(api, true)

function createRect(top: number) {
  return {
    top,
    bottom: top + 40,
    left: 0,
    right: 200,
    width: 200,
    height: 40,
    x: 0,
    y: top,
    toJSON: () => ({}),
  }
}

function createSection(overrides: Partial<TocSection> = {}): TocSection {
  return {
    id: 'intro',
    text: 'Introduction',
    level: 2,
    html: '',
    index: 0,
    anchorId: 'intro',
    pageStart: 3,
    ...overrides,
  }
}

describe('usePreviewProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
      callback(0)
      return 1
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('restores saved reading progress into the preview pane', async () => {
    mockedApi.getDocumentProgress.mockResolvedValue({
      has_progress: true,
      progress_percent: 40,
    } as never)

    const pane = document.createElement('div')
    Object.defineProperty(pane, 'scrollHeight', { configurable: true, value: 1000 })
    Object.defineProperty(pane, 'clientHeight', { configurable: true, value: 250 })
    Object.defineProperty(pane, 'scrollTop', { configurable: true, writable: true, value: 0 })

    const previewPaneRef = { current: pane }
    const onScrollProgress = vi.fn()

    const { result } = renderHook(() =>
      usePreviewProgress({
        documentId: 42,
        activeHtmlContent: '<p>Body</p>',
        selectedAttachmentId: null,
        previewPaneRef,
        activeHeading: null,
        setActiveHeading: vi.fn(),
        sections: [],
        readerCurrentPage: null,
        setReaderCurrentPage: vi.fn(),
        onScrollProgress,
        hasUser: true,
      }),
    )

    await waitFor(() => {
      expect(pane.scrollTop).toBe(300)
    })

    expect(result.current.previewScrollProgress).toBe(40)
    expect(onScrollProgress).toHaveBeenCalledWith(40)
  })

  it('tracks scroll progress and updates the active section and reader page', () => {
    const pane = document.createElement('div')
    const heading = document.createElement('h2')
    heading.id = 'intro'
    const laterHeading = document.createElement('h2')
    laterHeading.id = 'next'

    pane.appendChild(heading)
    pane.appendChild(laterHeading)

    Object.defineProperty(pane, 'scrollHeight', { configurable: true, value: 600 })
    Object.defineProperty(pane, 'clientHeight', { configurable: true, value: 100 })
    Object.defineProperty(pane, 'scrollTop', { configurable: true, writable: true, value: 150 })
    pane.getBoundingClientRect = vi.fn(() => createRect(0))
    heading.getBoundingClientRect = vi.fn(() => createRect(60))
    laterHeading.getBoundingClientRect = vi.fn(() => createRect(180))

    const setActiveHeading = vi.fn()
    const setReaderCurrentPage = vi.fn()
    const onScrollProgress = vi.fn()

    const { result } = renderHook(() =>
      usePreviewProgress({
        documentId: 42,
        activeHtmlContent: '<h2 id="intro">Introduction</h2>',
        selectedAttachmentId: 1,
        previewPaneRef: { current: pane },
        activeHeading: null,
        setActiveHeading,
        sections: [createSection()],
        readerCurrentPage: null,
        setReaderCurrentPage,
        onScrollProgress,
        hasUser: false,
      }),
    )

    act(() => {
      result.current.handleScroll({ currentTarget: pane } as React.UIEvent<HTMLDivElement>)
    })

    expect(result.current.previewScrollProgress).toBe(30)
    expect(onScrollProgress).toHaveBeenCalledWith(30)
    expect(setActiveHeading).toHaveBeenCalledWith('intro')
    expect(setReaderCurrentPage).toHaveBeenCalledWith(3)
  })
})
