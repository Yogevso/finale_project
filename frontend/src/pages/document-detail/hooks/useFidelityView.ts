import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import { extractApiErrorMessage } from '@/lib/toast'
import type { Attachment } from '@/types'

/**
 * Mirrors the backend's own PDF check (`_resolve_structured_reader_kind`); the fidelity
 * endpoint rejects anything else.
 */
export function supportsFidelityView(attachment: Attachment | null): boolean {
  if (!attachment) {
    return false
  }

  const mimeType = (attachment.mime_type || '').toLowerCase()
  const filename = (attachment.original_filename || attachment.filename || '').toLowerCase()
  return mimeType === 'application/pdf' || filename.endsWith('.pdf')
}

/**
 * The attachment the original-layout view renders.
 *
 * Deliberately not taken from `previewableAttachments`. That list drives the reader
 * *source* and holds only the formats with a reader artifact - DOCX and PPTX - so a PDF
 * is never in it, and reading the fidelity attachment from it made `supportsFidelityView`
 * a test that could not pass. The fidelity view is a rendering mode rather than a source,
 * so it picks its PDF out of the document's full attachment list and leaves the reader
 * source alone.
 */
export function getFidelityAttachment(attachments: Attachment[]): Attachment | null {
  return attachments.find(supportsFidelityView) ?? null
}

interface UseFidelityViewParams {
  documentId: number
  attachment: Attachment | null
  enabled: boolean
}

/**
 * Loads the page-faithful render of a PDF attachment. The backend regenerates it on every
 * call, so successful renders are kept per attachment for the life of the page.
 */
export function useFidelityView({ documentId, attachment, enabled }: UseFidelityViewParams) {
  const [fidelityHtml, setFidelityHtml] = useState<string | null>(null)
  const [fidelityError, setFidelityError] = useState<string | null>(null)
  const [isFidelityLoading, setIsFidelityLoading] = useState(false)
  const cacheRef = useRef(new Map<number, string>())

  const attachmentId = attachment && supportsFidelityView(attachment) ? attachment.id : null

  useEffect(() => {
    if (!enabled || attachmentId === null) {
      return
    }

    const cached = cacheRef.current.get(attachmentId)
    if (cached) {
      setFidelityHtml(cached)
      setFidelityError(null)
      return
    }

    let cancelled = false
    setFidelityHtml(null)
    setFidelityError(null)
    setIsFidelityLoading(true)

    const load = async () => {
      try {
        const view = await api.getAttachmentFidelityView(documentId, attachmentId)
        if (cancelled) {
          return
        }

        const html = view.html_content?.trim() ? view.html_content : null
        if (view.status === 'ready' && html) {
          cacheRef.current.set(attachmentId, html)
          setFidelityHtml(html)
          setFidelityError(null)
          return
        }

        setFidelityHtml(null)
        setFidelityError(view.error || 'Original layout is unavailable for this attachment.')
      } catch (loadError) {
        if (cancelled) {
          return
        }

        setFidelityHtml(null)
        setFidelityError(
          extractApiErrorMessage(loadError, 'Could not load the original layout.'),
        )
      } finally {
        if (!cancelled) {
          setIsFidelityLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [attachmentId, documentId, enabled])

  return { fidelityHtml, fidelityError, isFidelityLoading }
}
