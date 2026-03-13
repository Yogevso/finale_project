import { act, renderHook, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/lib/api'
import type { Attachment } from '@/types'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useReaderArtifact } from './useReaderArtifact'

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

describe('useReaderArtifact', () => {
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
      const hook = useReaderArtifact({
        documentId: 42,
        selectedAttachment,
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
      const [, setSections] = useState<TocSection[]>([])
      return useReaderArtifact({
        documentId: 42,
        selectedAttachment,
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

  it('preserves the fuller backend TOC order when html only exposes a subset of headings', async () => {
    const selectedAttachment = createAttachment()

    mockedApi.getAttachmentReaderView.mockResolvedValue({
      attachment_id: selectedAttachment.id,
      status: 'ready',
      html_content:
        '<article class="docx-document"><h1 id="heading-intro">Intro</h1><p>Body</p><h1 id="heading-appendix-a">Appendix A</h1></article>',
      toc_items: [
        {
          id: 'toc-0',
          level: 1,
          title: 'Intro',
          page: 1,
          page_start: 1,
          page_end: null,
          anchor_id: 'page-1',
        },
        {
          id: 'toc-1',
          level: 1,
          title: 'Release Kit Summary',
          page: 2,
          page_start: 2,
          page_end: null,
          anchor_id: 'page-2',
        },
        {
          id: 'toc-2',
          level: 1,
          title: 'Appendix A',
          page: 3,
          page_start: 3,
          page_end: null,
          anchor_id: 'page-3',
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
      const hook = useReaderArtifact({
        documentId: 42,
        selectedAttachment,
        setSections,
        processHtmlWithSections: (html) => html,
      })
      return { ...hook, sections }
    })

    await waitFor(() => {
      expect(result.current.sections.map((section) => section.text)).toEqual([
        'Intro',
        'Release Kit Summary',
        'Appendix A',
      ])
    })

    expect(result.current.sections[0]?.anchorId).toBe('heading-intro')
    expect(result.current.sections[1]?.anchorId).toBe('page-2')
    expect(result.current.sections[2]?.anchorId).toBe('heading-appendix-a')
  })
})
