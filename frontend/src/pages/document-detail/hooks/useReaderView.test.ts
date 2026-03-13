import { act, renderHook, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useReaderView } from '@/pages/document-detail/hooks/useReaderView'

vi.mock('@/lib/api', () => ({
  api: {
    getAttachmentReaderView: vi.fn(),
    retryAttachmentReaderView: vi.fn(),
  },
}))

const mockedApi = vi.mocked(api, true)

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
    reader_html_status: 'pending',
    ...overrides,
  }
}

describe('useReaderView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads reader artifact content and sections for the selected attachment', async () => {
    const selectedAttachment = createAttachment()
    const processHtmlWithSections = vi.fn((html: string) => `processed:${html}`)

    mockedApi.getAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'ready',
      html_content: '<h1 id="heading-1">Reader Intro</h1><p>Reader body</p>',
      toc_items: [
        {
          id: 'reader-1',
          level: 1,
          title: 'Reader Intro',
          page: 1,
          page_start: 1,
          page_end: null,
          anchor_id: 'heading-1',
        },
      ],
      toc_source: 'headings',
      error: null,
      generated_at: '2026-01-01T00:00:00Z',
      warnings: [],
      confidence: 0.98,
    } as never)

    const { result } = renderHook(() => {
      const [sections, setSections] = useState<TocSection[]>([])
      const hook = useReaderView({
        documentId: 42,
        selectedAttachment,
        sections,
        setSections,
        processHtmlWithSections,
      })
      return { ...hook, sections }
    })

    await waitFor(() => {
      expect(mockedApi.getAttachmentReaderView).toHaveBeenCalledWith(42, selectedAttachment.id)
      expect(result.current.readerHtmlContent).toBe(
        'processed:<h1 id="heading-1">Reader Intro</h1><p>Reader body</p>',
      )
      expect(result.current.sections[0]?.text).toBe('Reader Intro')
      expect(result.current.readerConfidence).toBe(0.98)
    })
  })

  it('resets reader state when the selected attachment is removed', async () => {
    const selectedAttachment = createAttachment()

    mockedApi.getAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'ready',
      html_content: '<h2 id="heading-2">Section</h2><p>Text</p>',
      toc_items: [],
      toc_source: 'headings',
      error: null,
      generated_at: '2026-01-01T00:00:00Z',
      warnings: [],
      confidence: 1,
    } as never)

    const initialProps: { attachment: Attachment | null } = {
      attachment: selectedAttachment,
    }

    const { result, rerender } = renderHook(
      ({ attachment }: { attachment: Attachment | null }) => {
        const [sections, setSections] = useState<TocSection[]>([])
        return useReaderView({
          documentId: 42,
          selectedAttachment: attachment,
          sections,
          setSections,
          processHtmlWithSections: (html) => html,
        })
      },
      {
        initialProps,
      },
    )

    await waitFor(() => {
      expect(result.current.readerHtmlContent).toContain('Section')
    })

    rerender({ attachment: null })

    await waitFor(() => {
      expect(result.current.readerHtmlContent).toBeNull()
      expect(result.current.readerStatus).toBeNull()
      expect(result.current.activeHeading).toBeNull()
    })
  })

  it('retries reader generation when requested', async () => {
    const selectedAttachment = createAttachment()

    mockedApi.getAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'failed',
      html_content: null,
      toc_items: [],
      toc_source: 'none',
      error: 'Extraction failed',
      generated_at: '2026-01-01T00:00:00Z',
      warnings: [],
      confidence: null,
    } as never)

    mockedApi.retryAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'ready',
      html_content: '<h2 id="retry-heading">Recovered</h2>',
      toc_items: [],
      toc_source: 'headings',
      error: null,
      generated_at: '2026-01-01T00:00:00Z',
      warnings: [],
      confidence: 0.91,
    } as never)

    const { result } = renderHook(() => {
      const [sections, setSections] = useState<TocSection[]>([])
      return useReaderView({
        documentId: 42,
        selectedAttachment,
        sections,
        setSections,
        processHtmlWithSections: (html) => html,
      })
    })

    await waitFor(() => {
      expect(result.current.readerError).toBe('Extraction failed')
    })

    await act(async () => {
      await result.current.handleRetryReaderView()
    })

    expect(mockedApi.retryAttachmentReaderView).toHaveBeenCalledWith(42, selectedAttachment.id)
    expect(result.current.readerHtmlContent).toContain('Recovered')
  })
})
