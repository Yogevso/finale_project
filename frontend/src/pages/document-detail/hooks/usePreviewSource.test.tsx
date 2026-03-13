import { useState } from 'react'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Attachment } from '@/types'
import { usePreviewSource } from './usePreviewSource'

function buildAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 1,
    document_id: 42,
    filename: 'file.docx',
    original_filename: 'file.docx',
    file_size: 128,
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_by: 7,
    uploaded_at: '2026-01-01T00:00:00Z',
    reader_html_status: 'pending',
    ...overrides,
  }
}

describe('usePreviewSource', () => {
  it('keeps the preview attachment selected and reports inline source when reader html is unavailable', async () => {
    const attachment = buildAttachment()

    const { result } = renderHook(() => {
      const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)
      const preview = usePreviewSource({
        attachments: [attachment],
        selectedAttachment,
        setSelectedAttachment,
        inlineContent: '<p>Inline body</p>',
        readerHtmlContent: null,
        readerStatus: 'processing',
      })

      return {
        selectedAttachment,
        ...preview,
      }
    })

    await waitFor(() => {
      expect(result.current.selectedAttachment?.id).toBe(attachment.id)
    })

    expect(result.current.previewSource).toBe('inline')
    expect(result.current.activeHtmlContent).toBe('<p>Inline body</p>')
    expect(result.current.showingReaderView).toBe(false)
    expect(result.current.previewState).toBe('READY')
  })

  it('clears stale attachment selection and falls back to download-only when no preview source exists', async () => {
    const attachment = buildAttachment()
    type PreviewSourceProps = {
      attachments: Attachment[]
      inlineContent: string | null
      readerHtmlContent: string | null
    }
    const initialProps: PreviewSourceProps = {
      attachments: [attachment],
      inlineContent: null,
      readerHtmlContent: '<h1>Reader</h1>',
    }

    const { result, rerender } = renderHook(
      ({ attachments, inlineContent, readerHtmlContent }: PreviewSourceProps) => {
        const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(attachment)
        const preview = usePreviewSource({
          attachments,
          selectedAttachment,
          setSelectedAttachment,
          inlineContent,
          readerHtmlContent,
          readerStatus: 'failed',
        })

        return {
          selectedAttachment,
          ...preview,
        }
      },
      {
        initialProps,
      },
    )

    expect(result.current.previewSource).toBe('reader')
    expect(result.current.showingReaderView).toBe(true)

    rerender({
      attachments: [
        buildAttachment({
          id: 2,
          filename: 'legacy.bin',
          original_filename: 'legacy.bin',
          mime_type: 'application/octet-stream',
        }),
      ],
      inlineContent: null,
      readerHtmlContent: null,
    })

    await waitFor(() => {
      expect(result.current.selectedAttachment).toBeNull()
    })

    expect(result.current.previewSource).toBe('none')
    expect(result.current.previewState).toBe('DOWNLOAD_ONLY')
  })

  it('does not churn selection state when attachments are recreated with the same values', async () => {
    const setSelectedAttachmentSpy = vi.fn()
    const initialAttachment = buildAttachment({ id: 17, reader_html_status: 'ready' })

    const { result, rerender } = renderHook(
      ({ attachments }: { attachments: Attachment[] }) =>
        usePreviewSource({
          attachments,
          selectedAttachment: initialAttachment,
          setSelectedAttachment: setSelectedAttachmentSpy,
          inlineContent: null,
          readerHtmlContent: '<h1>Reader</h1>',
          readerStatus: 'ready',
        }),
      {
        initialProps: {
          attachments: [initialAttachment],
        },
      },
    )

    rerender({
      attachments: [
        buildAttachment({
          id: 17,
          reader_html_status: 'ready',
        }),
      ],
    })

    await waitFor(() => {
      expect(result.current.previewSource).toBe('reader')
    })

    expect(setSelectedAttachmentSpy).not.toHaveBeenCalled()
  })
})
