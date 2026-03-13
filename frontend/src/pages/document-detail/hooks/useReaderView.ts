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
  resolveSectionPageStart,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers'

interface UseReaderViewParams {
  documentId: number
  selectedAttachment: Attachment | null
  sections: TocSection[]
  setSections: Dispatch<SetStateAction<TocSection[]>>
  processHtmlWithSections: (html: string) => string
}

export function useReaderView({
  documentId,
  selectedAttachment,
  sections,
  setSections,
  processHtmlWithSections,
}: UseReaderViewParams) {
  const [readerHtmlContent, setReaderHtmlContent] = useState<string | null>(null)
  const [readerStatus, setReaderStatus] = useState<AttachmentReaderViewResponse['status'] | null>(
    null,
  )
  const [readerWarnings, setReaderWarnings] = useState<AttachmentExtractionWarning[]>([])
  const [readerConfidence, setReaderConfidence] = useState<number | null>(null)
  const [readerError, setReaderError] = useState<string | null>(null)
  const [isReaderLoading, setIsReaderLoading] = useState(false)
  const [readerReloadToken, setReaderReloadToken] = useState(0)
  const [readerCurrentPage, setReaderCurrentPage] = useState<number | null>(null)
  const [activeHeading, setActiveHeading] = useState<string | null>(null)
  const processHtmlWithSectionsRef = useRef(processHtmlWithSections)

  useEffect(() => {
    processHtmlWithSectionsRef.current = processHtmlWithSections
  }, [processHtmlWithSections])

  const navigateReaderToSection = useCallback(
    (item: TocSection, behavior: ScrollBehavior = 'smooth') => {
      const anchorId = item.anchorId || `heading-${item.index}`
      const targetElement = document.getElementById(anchorId)
      const pageStart = resolveSectionPageStart(item)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior, block: 'start' })
        setActiveHeading(targetElement.id)
      } else {
        setActiveHeading(anchorId)
      }

      if (pageStart) {
        setReaderCurrentPage(pageStart)
      }
    },
    [],
  )

  useEffect(() => {
    setReaderStatus(selectedAttachment?.reader_html_status ?? null)
    setReaderWarnings([])
    setReaderConfidence(null)
    setReaderHtmlContent(null)
    setReaderError(null)
    setIsReaderLoading(false)
    setReaderReloadToken(0)
    setReaderCurrentPage(null)
    setActiveHeading(null)

    if (!selectedAttachment) {
      setSections([])
    }
  }, [selectedAttachment?.id, selectedAttachment?.reader_html_status, setSections, selectedAttachment])

  useEffect(() => {
    if (!selectedAttachment) {
      return
    }

    const attachmentId = selectedAttachment.id
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
          const processedHtml = processHtmlWithSectionsRef.current(readerView.html_content || '')
          const mappedTocSections = mapOutlineItemsToSections(readerView.toc_items || [])
          setReaderHtmlContent(processedHtml)
          setSections(mappedTocSections)
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
  }, [documentId, readerReloadToken, selectedAttachment, setSections])

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
        const processedHtml = processHtmlWithSectionsRef.current(payload.html_content)
        const mappedTocSections = mapOutlineItemsToSections(payload.toc_items || [])
        setReaderHtmlContent(processedHtml)
        setSections(mappedTocSections)
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
    readerCurrentPage,
    activeHeading,
    setReaderCurrentPage,
    setActiveHeading,
    navigateReaderToSection,
    handleRetryReaderView,
    hasReaderSections: sections.length > 0,
  }
}
