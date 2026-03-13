import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as domEnv from '@/env/dom'
import type { Attachment } from '@/types'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useOutlineNavigation } from './useOutlineNavigation'

vi.mock('@/env/dom', async () => {
  const actual = await vi.importActual<typeof import('@/env/dom')>('@/env/dom')
  return {
    ...actual,
    getDocument: vi.fn(() => document),
  }
})

function createAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 1,
    document_id: 42,
    filename: 'document.docx',
    original_filename: 'document.docx',
    file_size: 1024,
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    reader_html_status: 'ready',
    ...overrides,
  }
}

describe('useOutlineNavigation', () => {
  const scrollIntoViewMock = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(domEnv.getDocument).mockReturnValue(document)
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoViewMock,
    })
  })

  it('navigates to an existing heading and tracks page state', () => {
    document.body.innerHTML = '<h2 id="heading-1">Section</h2>'
    const section: TocSection = {
      id: 'section-1',
      index: 1,
      level: 2,
      text: 'Section',
      html: '',
      anchorId: 'heading-1',
      pageStart: 3,
      pageEnd: null,
    }

    const { result } = renderHook(() =>
      useOutlineNavigation({
        selectedAttachment: createAttachment(),
      }),
    )

    act(() => {
      result.current.navigateReaderToSection(section)
    })

    expect(scrollIntoViewMock).toHaveBeenCalled()
    expect(result.current.activeHeading).toBe('heading-1')
    expect(result.current.readerCurrentPage).toBe(3)
  })

  it('resets heading and page when the selected attachment changes', () => {
    const { result, rerender } = renderHook(
      ({ attachment }: { attachment: Attachment | null }) =>
        useOutlineNavigation({
          selectedAttachment: attachment,
        }),
      {
        initialProps: {
          attachment: createAttachment({ id: 1 }),
        },
      },
    )

    act(() => {
      result.current.setActiveHeading('heading-1')
      result.current.setReaderCurrentPage(4)
    })

    rerender({ attachment: createAttachment({ id: 2 }) })

    expect(result.current.activeHeading).toBeNull()
    expect(result.current.readerCurrentPage).toBeNull()
  })
})
