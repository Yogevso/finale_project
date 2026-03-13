import { useCallback, useEffect, useRef, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { api } from '@/lib/api'
import type {
  Attachment,
  AttachmentExtractionWarning,
  AttachmentReaderViewResponse,
} from '@/types'
import {
  mapOutlineItemsToSections,
  mergeTocSections,
  processHtmlIntoSections,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers'

interface UseReaderArtifactParams {
  documentId: number
  selectedAttachment: Attachment | null
  setSections: Dispatch<SetStateAction<TocSection[]>>
  processHtmlWithSections: (html: string) => string
}

export function useReaderArtifact({
  documentId,
  selectedAttachment,
  setSections,
  processHtmlWithSections,
}: UseReaderArtifactParams) {
  const selectedAttachmentId = selectedAttachment?.id ?? null
  const selectedAttachmentStatus = selectedAttachment?.reader_html_status ?? null
  const [readerHtmlContent, setReaderHtmlContent] = useState<string | null>(null)
  const [readerStatus, setReaderStatus] = useState<AttachmentReaderViewResponse['status'] | null>(
    null,
  )
  const [readerWarnings, setReaderWarnings] = useState<AttachmentExtractionWarning[]>([])
  const [readerConfidence, setReaderConfidence] = useState<number | null>(null)
  const [readerError, setReaderError] = useState<string | null>(null)
  const [isReaderLoading, setIsReaderLoading] = useState(false)
  const [readerReloadToken, setReaderReloadToken] = useState(0)
  const processHtmlWithSectionsRef = useRef(processHtmlWithSections)

  useEffect(() => {
    processHtmlWithSectionsRef.current = processHtmlWithSections
  }, [processHtmlWithSections])

  useEffect(() => {
    setReaderStatus(selectedAttachmentStatus)
    setReaderWarnings([])
    setReaderConfidence(null)
    setReaderHtmlContent(null)
    setReaderError(null)
    setIsReaderLoading(false)
    setReaderReloadToken(0)

    if (!selectedAttachmentId) {
      setSections([])
    }
  }, [selectedAttachmentId, selectedAttachmentStatus, setSections])

  useEffect(() => {
    if (!selectedAttachmentId) {
      return
    }

    const attachmentId = selectedAttachmentId
    let cancelled = false
    let pollTimer: number | null = null

    const loadReaderArtifact = async (initialLoad: boolean) => {
      if (initialLoad) {
        setIsReaderLoading(true)
        setReaderError(null)
      }

      try {
        const readerView = await api.getAttachmentReaderView(documentId, attachmentId)
        if (cancelled) {
          return
        }

        setReaderStatus(readerView.status)
        setReaderWarnings(readerView.warnings || [])
        setReaderConfidence(readerView.confidence ?? null)

        const isReadyWithContent =
          readerView.status === 'ready' && !!readerView.html_content?.trim()

        if (isReadyWithContent) {
          const sourceHtml = readerView.html_content || ''
          const processedHtml = processHtmlWithSectionsRef.current(sourceHtml)
          const htmlSections = processHtmlIntoSections(sourceHtml).sections
          const mappedTocSections = mapOutlineItemsToSections(readerView.toc_items || [])
          setReaderHtmlContent(processedHtml)
          setSections(mergeTocSections(mappedTocSections, htmlSections))
          setReaderError(null)
          setReaderReloadToken(0)
          setIsReaderLoading(false)
          return
        }

        setReaderHtmlContent(null)

        if (readerView.status === 'failed') {
          setReaderError(readerView.error || 'Reader View is unavailable for this attachment.')
          setIsReaderLoading(false)
          return
        }

        if (readerView.status === 'ready') {
          setReaderError(readerView.error || 'Reader View returned no previewable content.')
          setIsReaderLoading(false)
          return
        }

        setIsReaderLoading(false)
        pollTimer = window.setTimeout(() => {
          void loadReaderArtifact(false)
        }, 2000)
      } catch (loadError) {
        if (cancelled) {
          return
        }

        console.error('Reader View load error:', loadError)
        setReaderError('Failed to load Reader View.')
        setReaderHtmlContent(null)
        setIsReaderLoading(false)
      }
    }

    void loadReaderArtifact(true)

    return () => {
      cancelled = true
      if (pollTimer !== null) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [documentId, readerReloadToken, selectedAttachmentId, setSections])

  const handleRetryReaderView = useCallback(async () => {
    if (!selectedAttachment) {
      return
    }

    setIsReaderLoading(true)
    setReaderError(null)
    setReaderHtmlContent(null)
    setReaderStatus('pending')
    setReaderWarnings([])
    setReaderConfidence(null)

    try {
      const payload = await api.retryAttachmentReaderView(documentId, selectedAttachment.id)
      setReaderStatus(payload.status)
      setReaderWarnings(payload.warnings || [])
      setReaderConfidence(payload.confidence ?? null)
      if (payload.status === 'ready' && payload.html_content?.trim()) {
        const sourceHtml = payload.html_content
        const processedHtml = processHtmlWithSectionsRef.current(sourceHtml)
        const htmlSections = processHtmlIntoSections(sourceHtml).sections
        const mappedTocSections = mapOutlineItemsToSections(payload.toc_items || [])
        setReaderHtmlContent(processedHtml)
        setSections(mergeTocSections(mappedTocSections, htmlSections))
        setIsReaderLoading(false)
        return
      }

      setReaderReloadToken((previous) => previous + 1)
    } catch (retryError) {
      console.error('Reader View retry failed:', retryError)
      setReaderError('Retry failed.')
      setIsReaderLoading(false)
    }
  }, [documentId, selectedAttachment, setSections])

  return {
    readerHtmlContent,
    readerStatus,
    readerWarnings,
    readerConfidence,
    readerError,
    isReaderLoading,
    handleRetryReaderView,
  }
}
