import { act, renderHook, waitFor } from '@testing-library/react'
import { useRef, useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useReaderView } from '@/pages/document-detail/hooks/useReaderView'

vi.mock('@/lib/api', () => ({
  api: {
    getAttachmentOutline: vi.fn(),
    getAttachmentReaderView: vi.fn(),
    retryAttachmentReaderView: vi.fn(),
  },
}))

const mockedApi = vi.mocked(api, true)

function createAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 1,
    document_id: 42,
    filename: 'document.pdf',
    original_filename: 'document.pdf',
    file_size: 1024,
    mime_type: 'application/pdf',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    preview_pdf_status: 'ready',
    reader_html_status: 'ready',
    ...overrides,
  }
}

describe('useReaderView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads outline and reader artifact when switched to reader view', async () => {
    const selectedAttachment = createAttachment()
    const processHtmlWithSections = vi.fn((html: string) => `processed:${html}`)

    mockedApi.getAttachmentOutline.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      has_outline: true,
      items: [
        {
          id: 'outline-1',
          level: 1,
          title: 'Outline Intro',
          page: 1,
          page_start: 1,
          page_end: null,
          anchor_id: 'pdf-page-1',
        },
      ],
      source: 'outline',
      error: null,
    } as never)

    mockedApi.getAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'ready',
      html_content: '<h1>Reader Intro</h1><p>Reader body</p>',
      toc_items: [
        {
          id: 'reader-1',
          level: 1,
          title: 'Reader Intro',
          page: 1,
          page_start: 1,
          page_end: null,
          anchor_id: 'pdf-page-1',
        },
      ],
      toc_source: 'outline',
      error: null,
      generated_at: '2026-01-01T00:00:00Z',
    } as never)

    const { result } = renderHook(() => {
      const [sections, setSections] = useState<TocSection[]>([])
      const previewPaneRef = useRef<HTMLDivElement>(null)
      const hook = useReaderView({
        documentId: 42,
        selectedAttachment,
        isSelectedPdf: true,
        sections,
        setSections,
        processHtmlWithSections,
        previewPaneRef,
      })
      return { ...hook, sections }
    })

    await waitFor(() => {
      expect(mockedApi.getAttachmentOutline).toHaveBeenCalledWith(42, selectedAttachment.id)
    })

    act(() => {
      result.current.handleSwitchToReaderView()
    })

    await waitFor(() => {
      expect(mockedApi.getAttachmentReaderView).toHaveBeenCalledWith(42, selectedAttachment.id)
      expect(result.current.pdfPreviewMode).toBe('reader')
      expect(result.current.readerHtmlContent).toBe(
        'processed:<h1>Reader Intro</h1><p>Reader body</p>',
      )
      expect(result.current.sections.length).toBeGreaterThan(0)
      expect(result.current.sections[0].text).toBe('Reader Intro')
    })

    expect(processHtmlWithSections).toHaveBeenCalledWith('<h1>Reader Intro</h1><p>Reader body</p>')
  })

  it('resets reader state when PDF selection is removed', async () => {
    const selectedAttachment = createAttachment()

    mockedApi.getAttachmentOutline.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      has_outline: false,
      items: [],
      source: 'none',
      error: 'No TOC available',
    } as never)

    mockedApi.getAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'ready',
      html_content: '<h2>Section</h2><p>Text</p>',
      toc_items: [],
      toc_source: 'none',
      error: null,
      generated_at: '2026-01-01T00:00:00Z',
    } as never)

    const initialProps: { attachment: Attachment | null; isSelectedPdf: boolean } = {
      attachment: selectedAttachment,
      isSelectedPdf: true,
    }

    const { result, rerender } = renderHook(
      ({
        attachment,
        isSelectedPdf,
      }: {
        attachment: Attachment | null
        isSelectedPdf: boolean
      }) => {
        const [sections, setSections] = useState<TocSection[]>([])
        const previewPaneRef = useRef<HTMLDivElement>(null)
        return useReaderView({
          documentId: 42,
          selectedAttachment: attachment,
          isSelectedPdf,
          sections,
          setSections,
          processHtmlWithSections: (html) => html,
          previewPaneRef,
        })
      },
      {
        initialProps,
      },
    )

    act(() => {
      result.current.handleSwitchToReaderView()
    })

    await waitFor(() => {
      expect(result.current.pdfPreviewMode).toBe('reader')
    })

    rerender({ attachment: null, isSelectedPdf: false })

    await waitFor(() => {
      expect(result.current.pdfPreviewMode).toBe('original')
      expect(result.current.readerHtmlContent).toBeNull()
      expect(result.current.activeHeading).toBeNull()
      expect(result.current.pdfOutlineSections).toEqual([])
    })
  })
})
