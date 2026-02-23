import { useCallback, useEffect, useRef, useState } from 'react'
import type { Dispatch, RefObject, SetStateAction } from 'react'
import { api } from '@/lib/api'
import type { Attachment, AttachmentReaderViewResponse } from '@/types'
import {
  mapOutlineItemsToSections,
  parsePageFromAnchorId,
  resolveSectionPageStart,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers'

export type PdfPreviewMode = 'original' | 'reader'

interface UseReaderViewParams {
  documentId: number
  selectedAttachment: Attachment | null
  isSelectedPdf: boolean
  sections: TocSection[]
  setSections: Dispatch<SetStateAction<TocSection[]>>
  processHtmlWithSections: (html: string) => string
  previewPaneRef: RefObject<HTMLDivElement>
}

export function useReaderView({
  documentId,
  selectedAttachment,
  isSelectedPdf,
  sections,
  setSections,
  processHtmlWithSections,
  previewPaneRef,
}: UseReaderViewParams) {
  const [readerHtmlContent, setReaderHtmlContent] = useState<string | null>(null)
  const [readerStatus, setReaderStatus] = useState<AttachmentReaderViewResponse['status'] | null>(
    null,
  )
  const [readerError, setReaderError] = useState<string | null>(null)
  const [pdfPreviewMode, setPdfPreviewMode] = useState<PdfPreviewMode>('original')
  const [isReaderLoading, setIsReaderLoading] = useState(false)
  const [readerReloadToken, setReaderReloadToken] = useState(0)
  const [pdfOutlineSections, setPdfOutlineSections] = useState<TocSection[]>([])
  const [pdfOutlineLoading, setPdfOutlineLoading] = useState(false)
  const [pdfOutlineError, setPdfOutlineError] = useState<string | null>(null)
  const [pdfOutlinePage, setPdfOutlinePage] = useState<number | null>(null)
  const [readerCurrentPage, setReaderCurrentPage] = useState<number | null>(null)
  const [activeHeading, setActiveHeading] = useState<string | null>(null)
  const readerSyncNeededRef = useRef(false)

  const showingReaderView = isSelectedPdf && pdfPreviewMode === 'reader'
  const showingOriginalPdf = isSelectedPdf && pdfPreviewMode === 'original'

  const getVisibleReaderPage = useCallback((container: HTMLElement): number | null => {
    const pageSections = Array.from(
      container.querySelectorAll<HTMLElement>('section.pdf-reader-page[data-page]'),
    )
    if (pageSections.length === 0) {
      return null
    }

    const containerRect = container.getBoundingClientRect()
    const thresholdTop = containerRect.top + 110
    let currentPage: number | null = null

    pageSections.forEach((section) => {
      const pageValue = Number(section.dataset.page || '')
      if (!Number.isFinite(pageValue) || pageValue <= 0) return
      const rect = section.getBoundingClientRect()
      if (rect.top <= thresholdTop) {
        currentPage = pageValue
      } else if (currentPage === null) {
        currentPage = pageValue
      }
    })

    return currentPage
  }, [])

  const navigateReaderToSection = useCallback(
    (item: TocSection, behavior: ScrollBehavior = 'smooth') => {
      const anchorId = item.anchorId || `heading-${item.index}`
      const pageStart = resolveSectionPageStart(item)
      const pageAnchorId = pageStart ? `pdf-page-${pageStart}` : null
      const targetElement =
        document.getElementById(anchorId) ||
        (pageAnchorId ? document.getElementById(pageAnchorId) : null)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior, block: 'start' })
      }

      if (pageStart) {
        setPdfOutlinePage(pageStart)
        setReaderCurrentPage(pageStart)
      }

      if (targetElement?.id) {
        setActiveHeading(targetElement.id)
      } else if (anchorId) {
        setActiveHeading(anchorId)
      }
    },
    [],
  )

  useEffect(() => {
    if (!isSelectedPdf) {
      readerSyncNeededRef.current = false
      setPdfPreviewMode('original')
      setReaderStatus(null)
      setReaderHtmlContent(null)
      setReaderError(null)
      setIsReaderLoading(false)
      setReaderReloadToken(0)
      setPdfOutlineSections([])
      setPdfOutlineLoading(false)
      setPdfOutlineError(null)
      setPdfOutlinePage(null)
      setReaderCurrentPage(null)
      setActiveHeading(null)
      return
    }

    readerSyncNeededRef.current = false
    setPdfPreviewMode('original')
    setReaderStatus(selectedAttachment?.reader_html_status ?? null)
    setReaderHtmlContent(null)
    setReaderError(null)
    setIsReaderLoading(false)
    setReaderReloadToken(0)
    setPdfOutlinePage(null)
    setReaderCurrentPage(null)
    setActiveHeading(null)
  }, [isSelectedPdf, selectedAttachment?.id, selectedAttachment?.reader_html_status])

  useEffect(() => {
    if (!isSelectedPdf || !selectedAttachment) {
      setPdfOutlineSections([])
      setPdfOutlineLoading(false)
      setPdfOutlineError(null)
      return
    }

    let cancelled = false
    setPdfOutlineLoading(true)
    setPdfOutlineError(null)

    api
      .getAttachmentOutline(documentId, selectedAttachment.id)
      .then((outlinePayload) => {
        if (cancelled) return
        const mappedSections = mapOutlineItemsToSections(outlinePayload.items || [])
        setPdfOutlineSections(mappedSections)
        if (mappedSections.length === 0) {
          setPdfOutlineError(outlinePayload.error || 'No TOC available')
        } else {
          setPdfOutlineError(outlinePayload.error || null)
        }
      })
      .catch((outlineError) => {
        if (cancelled) return
        console.error('Failed loading PDF TOC:', outlineError)
        setPdfOutlineSections([])
        setPdfOutlineError('Failed to load TOC')
      })
      .finally(() => {
        if (!cancelled) {
          setPdfOutlineLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [documentId, isSelectedPdf, selectedAttachment])

  useEffect(() => {
    if (!showingReaderView || !selectedAttachment) return
    if (readerHtmlContent) return

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
        if (cancelled) return

        setReaderStatus(readerView.status)
        const isReadyWithContent =
          readerView.status === 'ready' && !!readerView.html_content?.trim()

        if (isReadyWithContent) {
          const processedHtml = processHtmlWithSections(readerView.html_content || '')
          const mappedTocSections = mapOutlineItemsToSections(readerView.toc_items || [])
          setReaderHtmlContent(processedHtml)
          if (mappedTocSections.length > 0) {
            setSections(mappedTocSections)
            setPdfOutlineSections(mappedTocSections)
            setPdfOutlineError(null)
          }
          setReaderError(null)
          setReaderReloadToken(0)
          setIsReaderLoading(false)
          return
        }

        setReaderHtmlContent(null)

        const shouldFallbackToOriginal =
          readerView.status === 'failed' ||
          (readerView.status === 'ready' && !readerView.html_content?.trim())
        if (shouldFallbackToOriginal) {
          setReaderError(readerView.error || 'Reader View is unavailable for this PDF.')
          setPdfPreviewMode('original')
          setIsReaderLoading(false)
          return
        }

        setIsReaderLoading(false)
        pollTimer = window.setTimeout(() => {
          void loadReaderArtifact(false)
        }, 2000)
      } catch (loadError) {
        if (cancelled) return
        console.error('Reader View load error:', loadError)
        setReaderError('Failed to load Reader View. Showing original PDF.')
        setReaderHtmlContent(null)
        setPdfPreviewMode('original')
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
  }, [
    documentId,
    processHtmlWithSections,
    readerHtmlContent,
    readerReloadToken,
    selectedAttachment,
    setSections,
    showingReaderView,
  ])

  const handleRetryReaderView = useCallback(async () => {
    if (!selectedAttachment) return

    setIsReaderLoading(true)
    setReaderError(null)
    setReaderHtmlContent(null)
    setReaderStatus('pending')

    try {
      const payload = await api.retryAttachmentReaderView(documentId, selectedAttachment.id)
      setReaderStatus(payload.status)
      if (payload.status === 'ready' && payload.html_content?.trim()) {
        const processedHtml = processHtmlWithSections(payload.html_content)
        const mappedTocSections = mapOutlineItemsToSections(payload.toc_items || [])
        setReaderHtmlContent(processedHtml)
        if (mappedTocSections.length > 0) {
          setSections(mappedTocSections)
          setPdfOutlineSections(mappedTocSections)
          setPdfOutlineError(null)
        }
        setIsReaderLoading(false)
        return
      }
      setReaderReloadToken((prev) => prev + 1)
    } catch (retryError) {
      console.error('Reader View retry failed:', retryError)
      setReaderError('Retry failed. Showing original PDF.')
      setPdfPreviewMode('original')
      setIsReaderLoading(false)
    }
  }, [documentId, processHtmlWithSections, selectedAttachment, setSections])

  useEffect(() => {
    if (!showingReaderView || !readerHtmlContent) return
    if (!readerSyncNeededRef.current) return

    readerSyncNeededRef.current = false
    const pageFromActiveHeading = parsePageFromAnchorId(activeHeading)
    const fallbackSections = sections.length > 0 ? sections : pdfOutlineSections
    const fallbackTocPage =
      fallbackSections.length > 0 ? resolveSectionPageStart(fallbackSections[0]) : null
    const targetPage = pdfOutlinePage || pageFromActiveHeading || fallbackTocPage || null
    const targetAnchorId = activeHeading || (targetPage ? `pdf-page-${targetPage}` : null)

    const rafId = window.requestAnimationFrame(() => {
      const pane = previewPaneRef.current
      const targetElement =
        (targetAnchorId ? document.getElementById(targetAnchorId) : null) ||
        (targetPage ? document.getElementById(`pdf-page-${targetPage}`) : null)

      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'auto', block: 'start' })
        if (targetElement.id) {
          setActiveHeading(targetElement.id)
        }
      }

      const visiblePage = pane ? getVisibleReaderPage(pane) : null
      const resolvedPage = targetPage || visiblePage
      if (resolvedPage) {
        setReaderCurrentPage(resolvedPage)
        setPdfOutlinePage((previous) => (previous === resolvedPage ? previous : resolvedPage))
      }
    })

    return () => {
      window.cancelAnimationFrame(rafId)
    }
  }, [
    activeHeading,
    getVisibleReaderPage,
    pdfOutlinePage,
    pdfOutlineSections,
    previewPaneRef,
    readerHtmlContent,
    sections,
    showingReaderView,
  ])

  const handleSwitchToOriginalPdf = useCallback(() => {
    readerSyncNeededRef.current = false
    setPdfPreviewMode('original')
  }, [])

  const handleSwitchToReaderView = useCallback(() => {
    readerSyncNeededRef.current = true
    const fallbackPage =
      pdfOutlinePage ||
      readerCurrentPage ||
      parsePageFromAnchorId(activeHeading) ||
      (pdfOutlineSections.length > 0 ? resolveSectionPageStart(pdfOutlineSections[0]) : null)

    if (fallbackPage) {
      setPdfOutlinePage(fallbackPage)
      setReaderCurrentPage(fallbackPage)
      if (!activeHeading) {
        setActiveHeading(`pdf-page-${fallbackPage}`)
      }
    }
    setPdfPreviewMode('reader')
  }, [activeHeading, pdfOutlinePage, pdfOutlineSections, readerCurrentPage])

  return {
    readerHtmlContent,
    readerStatus,
    readerError,
    pdfPreviewMode,
    isReaderLoading,
    pdfOutlineSections,
    pdfOutlineLoading,
    pdfOutlineError,
    pdfOutlinePage,
    readerCurrentPage,
    activeHeading,
    showingReaderView,
    showingOriginalPdf,
    setPdfOutlinePage,
    setReaderCurrentPage,
    setActiveHeading,
    getVisibleReaderPage,
    navigateReaderToSection,
    handleRetryReaderView,
    handleSwitchToOriginalPdf,
    handleSwitchToReaderView,
  }
}
