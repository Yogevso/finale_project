import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { CSSProperties } from 'react'
import type { ReadingWidth } from '@/lib/readingWidth'
import PdfPreviewPanel, { type PdfTocItem } from '@/components/PdfPreviewPanel'
import {
  getPreferredPreviewAttachment,
  resolveSelectedAttachment,
} from '@/lib/attachmentSelection'
import type { Attachment } from '@/types'
import {
  applyHighlights,
  getUsableVersionContent,
  processHtmlIntoSections,
  resolveSectionPageStart,
  type TocSection,
} from '@/pages/document-detail/helpers/previewHelpers'
import { ContentEditChooserPopup } from '@/pages/document-detail/components/ContentEditChooserPopup'
import { PreviewCanvas } from '@/pages/document-detail/components/PreviewCanvas'
import { PreviewToolbar } from '@/pages/document-detail/components/PreviewToolbar'
import { SectionEditPopup } from '@/pages/document-detail/components/SectionEditPopup'
import { TocPanel } from '@/pages/document-detail/components/TocPanel'
import { useContentEditingFlow } from '@/pages/document-detail/hooks/useContentEditingFlow'
import { useInlineComments } from '@/pages/document-detail/hooks/useInlineComments'
import { useReaderView } from '@/pages/document-detail/hooks/useReaderView'
import {
  DOCUMENT_FONT_SIZE_VALUES,
  getDocumentFontSize,
  getDocumentTheme,
  getDocumentThemeClassName,
  setDocumentFontSize,
  setDocumentTheme,
  type DocumentFontSize,
  type DocumentTheme,
} from '@/lib/documentReadingPreferences'

// Document Preview Component
const WORDS_PER_MINUTE = 200

function estimateReadingTimeMinutes(html: string | null): number | null {
  if (!html) {
    return null
  }

  const textContent = new DOMParser().parseFromString(html, 'text/html').body.textContent ?? ''
  const wordCount = textContent.trim().split(/\s+/).filter(Boolean).length

  if (wordCount === 0) {
    return null
  }

  return Math.max(1, Math.ceil(wordCount / WORDS_PER_MINUTE))
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  if (target.isContentEditable) {
    return true
  }

  const tagName = target.tagName.toLowerCase()
  return tagName === 'input' || tagName === 'textarea' || tagName === 'select'
}

export function DocumentPreview({
  documentId,
  attachments,
  documentTitle,
  onScrollProgress,
  onReadingTimeChange,
  isEditor,
  isFullscreen = false,
  showCanvasTitle = true,
  sectionLinkBasePath,
  widthMode = 'reading',
  contentEditRequestToken = 0,
  onToggleFullscreen,
}: {
  documentId: number
  attachments: Attachment[]
  documentTitle?: string
  onScrollProgress?: (progress: number) => void
  onReadingTimeChange?: (minutes: number | null) => void
  isEditor?: boolean
  isFullscreen?: boolean
  showCanvasTitle?: boolean
  sectionLinkBasePath: string
  widthMode?: ReadingWidth
  contentEditRequestToken?: number
  onToggleFullscreen?: () => void
}) {
  const { user } = useAuth()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)
  const [pdfPreviewUnavailableError, setPdfPreviewUnavailableError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [sections, setSections] = useState<TocSection[]>([])
  const [tocCollapsed, setTocCollapsed] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchMatchCount, setSearchMatchCount] = useState(0)
  const [activeSearchMatchIndex, setActiveSearchMatchIndex] = useState(-1)
  const [hasInlineContent, setHasInlineContent] = useState(false)
  const [previewScrollProgress, setPreviewScrollProgress] = useState(0)
  const [fontSize, setFontSizeState] = useState<DocumentFontSize>(() => getDocumentFontSize())
  const [theme, setThemeState] = useState<DocumentTheme>(() => getDocumentTheme())
  const previewPaneRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const restoredProgressKeyRef = useRef<string | null>(null)
  const {
    selectionPopup,
    commentPopup,
    commentText,
    isPrivateComment,
    isSubmittingComment,
    setCommentText,
    setIsPrivateComment,
    handleMouseUp,
    handleOpenCommentForm,
    handleSubmitComment,
    handleCloseCommentPopup,
  } = useInlineComments(documentId)

  // All attachments participate in preview-pdf pipeline.
  const previewableAttachments = useMemo(() => attachments, [attachments])

  const handleSetFontSize = useCallback((value: DocumentFontSize) => {
    setFontSizeState(value)
    setDocumentFontSize(value)
  }, [])

  const handleSetTheme = useCallback((value: DocumentTheme) => {
    setThemeState(value)
    setDocumentTheme(value)
  }, [])

  const isWordDoc = (att: Attachment | null) => {
    if (!att) return false
    return (
      att.mime_type === 'application/msword' ||
      att.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
  }

  const hasPreviewPdf = (att: Attachment | null) => {
    if (!att) return false
    if (att.preview_pdf_status === 'ready') return true
    return att.mime_type.startsWith('application/pdf')
  }

  const isPreviewPending = (att: Attachment | null) => {
    if (!att) return false
    return att.preview_pdf_status === 'pending' || att.preview_pdf_status === 'processing'
  }

  const isPreviewFailed = (att: Attachment | null) => {
    if (!att) return false
    return att.preview_pdf_status === 'failed'
  }

  const isSelectedPdf = hasPreviewPdf(selectedAttachment)

  const processHtmlWithSections = useCallback((html: string) => {
    const processed = processHtmlIntoSections(html)
    setSections(processed.sections)
    return processed.html
  }, [])

  const {
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
  } = useReaderView({
    documentId,
    selectedAttachment,
    isSelectedPdf,
    sections,
    setSections,
    processHtmlWithSections,
    previewPaneRef,
  })

  const activeHtmlContent = showingReaderView ? readerHtmlContent : htmlContent
  const shouldRenderHtmlPreview = showingReaderView
    ? !!activeHtmlContent
    : !isSelectedPdf && !!activeHtmlContent
  const contentStyle = useMemo(
    () =>
      ({
        '--doc-font-size': DOCUMENT_FONT_SIZE_VALUES[fontSize],
      }) as CSSProperties,
    [fontSize],
  )

  const focusSearchMatch = useCallback((targetIndex: number, behavior: ScrollBehavior = 'smooth') => {
    const container = document.getElementById('document-content-area')
    if (!container) {
      setSearchMatchCount(0)
      setActiveSearchMatchIndex(-1)
      return
    }

    const matches = Array.from(container.querySelectorAll<HTMLElement>('mark.doc-highlight'))
    if (matches.length === 0) {
      setSearchMatchCount(0)
      setActiveSearchMatchIndex(-1)
      return
    }

    const normalizedIndex = ((targetIndex % matches.length) + matches.length) % matches.length
    matches.forEach((match, index) => {
      match.classList.toggle('doc-highlight--active', index === normalizedIndex)
    })
    matches[normalizedIndex]?.scrollIntoView({ behavior, block: 'center' })
    setSearchMatchCount(matches.length)
    setActiveSearchMatchIndex(normalizedIndex)
  }, [])

  const handlePreviousSearchMatch = useCallback(() => {
    if (searchMatchCount === 0) {
      return
    }
    focusSearchMatch(activeSearchMatchIndex - 1)
  }, [activeSearchMatchIndex, focusSearchMatch, searchMatchCount])

  const handleNextSearchMatch = useCallback(() => {
    if (searchMatchCount === 0) {
      return
    }
    focusSearchMatch(activeSearchMatchIndex + 1)
  }, [activeSearchMatchIndex, focusSearchMatch, searchMatchCount])

  const applyProcessedHtml = useCallback(
    (html: string) => {
      setHtmlContent(processHtmlWithSections(html))
    },
    [processHtmlWithSections],
  )

  const {
    showContentEditChooser,
    editingSection,
    handleCloseContentEditChooser,
    handleStartEditingSection,
    handleChooseEditSection,
    handleChooseAddSection,
    handleCloseSectionEdit,
    handleBackToChooser,
    handleSaveSection,
  } = useContentEditingFlow({
    documentId,
    isEditor,
    contentEditRequestToken,
    showingReaderView,
    activeHtmlContent,
    isLoading,
    sections,
    applyProcessedHtml,
    onRequireOriginalPdf: handleSwitchToOriginalPdf,
  })

  // Calculate scroll progress.
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget
    const scrollTop = container.scrollTop
    const scrollHeight = container.scrollHeight - container.clientHeight
    const containerRect = container.getBoundingClientRect()

    if (scrollHeight > 0) {
      const progress = Math.min(100, Math.round((scrollTop / scrollHeight) * 100))
      setPreviewScrollProgress(progress)
      onScrollProgress?.(progress)
    } else {
      setPreviewScrollProgress(0)
    }

    if (showingReaderView) {
      const visiblePage = getVisibleReaderPage(container)
      if (visiblePage && visiblePage !== readerCurrentPage) {
        setReaderCurrentPage(visiblePage)
        setPdfOutlinePage((previous) => (previous === visiblePage ? previous : visiblePage))
      }
    }

    // Update active heading based on scroll position.
    const headings = container.querySelectorAll(
      'h1[id], h2[id], h3[id], h4[id], h5[id], h6[id], section[id^="pdf-page-"]',
    )
    let currentActive = null

    headings.forEach((heading) => {
      const rect = heading.getBoundingClientRect()
      if (rect.top <= containerRect.top + 100) {
        currentActive = heading.id
      }
    })

    if (currentActive && currentActive !== activeHeading) {
      setActiveHeading(currentActive)
    }
  }

  useEffect(() => {
    const container = document.getElementById('document-content-area')
    if (!activeHtmlContent || !container) {
      setSearchMatchCount(0)
      setActiveSearchMatchIndex(-1)
      return
    }

    applyHighlights(container, searchTerm)
    const matches = container.querySelectorAll('mark.doc-highlight')
    if (matches.length === 0) {
      setSearchMatchCount(0)
      setActiveSearchMatchIndex(-1)
      return
    }

    focusSearchMatch(0, 'auto')
  }, [activeHtmlContent, focusSearchMatch, searchTerm])

  useEffect(() => {
    onReadingTimeChange?.(estimateReadingTimeMinutes(activeHtmlContent))
  }, [activeHtmlContent, onReadingTimeChange])

  useEffect(() => {
    if (!activeHtmlContent) {
      setPreviewScrollProgress(0)
      return
    }

    setPreviewScrollProgress(0)
  }, [activeHtmlContent])

  useEffect(() => {
    if (!user || !activeHtmlContent || !previewPaneRef.current) {
      return
    }

    const restoreKey = `${documentId}:${selectedAttachment?.id ?? 'inline'}:${
      showingReaderView ? 'reader' : 'html'
    }`
    if (restoredProgressKeyRef.current === restoreKey) {
      return
    }
    restoredProgressKeyRef.current = restoreKey

    let cancelled = false
    let rafOne: number | null = null
    let rafTwo: number | null = null

    api
      .getDocumentProgress(documentId)
      .then((progress) => {
        if (cancelled || !progress.has_progress || !previewPaneRef.current) {
          return
        }

        rafOne = window.requestAnimationFrame(() => {
          rafTwo = window.requestAnimationFrame(() => {
            const pane = previewPaneRef.current
            if (!pane) {
              return
            }

            const scrollRange = pane.scrollHeight - pane.clientHeight
            if (scrollRange <= 0) {
              return
            }

            pane.scrollTop = Math.round(scrollRange * (progress.progress_percent / 100))
            setPreviewScrollProgress(progress.progress_percent)
            onScrollProgress?.(progress.progress_percent)
          })
        })
      })
      .catch(() => {
        // Ignore unavailable progress records or role-gated responses.
      })

    return () => {
      cancelled = true
      if (rafOne !== null) {
        window.cancelAnimationFrame(rafOne)
      }
      if (rafTwo !== null) {
        window.cancelAnimationFrame(rafTwo)
      }
    }
  }, [
    activeHtmlContent,
    documentId,
    onScrollProgress,
    selectedAttachment?.id,
    showingReaderView,
    user,
  ])

  useEffect(() => {
    const nextSelection = resolveSelectedAttachment(
      previewableAttachments,
      selectedAttachment,
      getPreferredPreviewAttachment,
    )
    if (nextSelection !== selectedAttachment) {
      setSelectedAttachment(nextSelection)
    }
  }, [previewableAttachments, selectedAttachment])

  useEffect(() => {
    const loadPreview = async () => {
      setIsLoading(true)
      setError(null)
      
      try {
        if (previewableAttachments.length > 0) {
          const resolvedSelection = resolveSelectedAttachment(
            previewableAttachments,
            selectedAttachment,
            getPreferredPreviewAttachment,
          )

          if (resolvedSelection !== selectedAttachment) {
            setSelectedAttachment(resolvedSelection)
            setIsLoading(false)
            return
          }

          if (resolvedSelection && hasPreviewPdf(resolvedSelection)) {
            setHasInlineContent(false)
            setHtmlContent(null)
            setSections([])
            setPreviewUrl(api.getAttachmentPreviewUrl(documentId, resolvedSelection.id))
            setIsLoading(false)
            return
          }

          if (resolvedSelection && isPreviewPending(resolvedSelection)) {
            setHasInlineContent(false)
            setPreviewUrl(null)
            setHtmlContent(null)
            setSections([])
            setError(null)
            setIsLoading(false)
            return
          }

          if (resolvedSelection && isPreviewFailed(resolvedSelection)) {
            setHasInlineContent(false)
            setPreviewUrl(null)
            setHtmlContent(null)
            setSections([])
            setError(
              resolvedSelection.preview_pdf_error ||
                'Preview PDF generation failed for this attachment.',
            )
            setIsLoading(false)
            return
          }
        }

        // First, check if there's version content (published preferred, else latest draft)
        const versionsResponse = await api.getVersions(documentId)
        const withContent = versionsResponse.items.filter((v) => !!getUsableVersionContent(v.content))
        const publishedVersion = withContent
          .filter(v => v.is_published)
          .sort((a, b) => new Date(b.published_at || b.created_at).getTime() - new Date(a.published_at || a.created_at).getTime())[0]
        const latestVersion = withContent
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
        let versionToShow = publishedVersion || latestVersion

        if (!versionToShow && versionsResponse.items.length > 0) {
          // Fallback: list payload can omit/trim content; fetch details until a usable version is found.
          const prioritizedIds = [
            ...new Set([
              ...versionsResponse.items
                .filter((version) => version.is_published)
                .sort(
                  (a, b) =>
                    new Date(b.published_at || b.created_at).getTime() -
                    new Date(a.published_at || a.created_at).getTime(),
                )
                .map((version) => version.id),
              ...versionsResponse.items
                .sort(
                  (a, b) =>
                    new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
                )
                .map((version) => version.id),
            ]),
          ]

          for (const versionId of prioritizedIds) {
            const fullVersion = await api.getVersion(documentId, versionId)
            if (getUsableVersionContent(fullVersion?.content)) {
              versionToShow = fullVersion
              break
            }
          }
        }

        const versionContent = getUsableVersionContent(versionToShow?.content)
        if (versionContent) {
          // Created-in-app document fallback: no attachments available.
          const processedHtml = processHtmlWithSections(versionContent)
          setHtmlContent(processedHtml)
          setPreviewUrl(null)
          setHasInlineContent(true)
          setIsLoading(false)
          return
        }
        
        // No inline content and no ready preview artifact.
        setHasInlineContent(false)
        setPreviewUrl(null)
        setHtmlContent(null)
        setSections([])
      } catch (e) {
        console.error('Preview load error:', e)
        setError('Failed to load preview')
        setPreviewUrl(null)
        setHtmlContent(null)
        setSections([])
      } finally {
        setIsLoading(false)
      }
    }

    loadPreview()
  }, [documentId, previewableAttachments, processHtmlWithSections, selectedAttachment])

  useEffect(() => {
    return () => {
      if (previewUrl?.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  useEffect(() => {
    if (!showingOriginalPdf || !previewUrl || !selectedAttachment) {
      setPdfPreviewUnavailableError(null)
    }
  }, [previewUrl, selectedAttachment, showingOriginalPdf])

  const tocSectionsForHtml =
    showingReaderView && sections.length === 0 ? pdfOutlineSections : sections

  const handleReaderTocClick = useCallback(
    (item: TocSection) => {
      navigateReaderToSection(item, 'smooth')
    },
    [navigateReaderToSection],
  )

  const handlePdfTocClick = useCallback(
    (item: TocSection) => {
      const pageStart = resolveSectionPageStart(item)
      const anchorId = item.anchorId || (pageStart ? `pdf-page-${pageStart}` : `heading-${item.index}`)
      if (pageStart) {
        setPdfOutlinePage(pageStart)
        setReaderCurrentPage(pageStart)
      }
      setActiveHeading(anchorId)
    },
    [setActiveHeading, setPdfOutlinePage, setReaderCurrentPage],
  )

  const handlePdfIframeError = useCallback(() => {
    setPdfPreviewUnavailableError('PDF preview unavailable. Please download original.')
  }, [])

  const activeSectionIndex = useMemo(() => {
    const activeSections = shouldRenderHtmlPreview ? tocSectionsForHtml : pdfOutlineSections
    if (activeSections.length === 0) {
      return -1
    }

    return activeSections.findIndex((item) => {
      const pageStart = resolveSectionPageStart(item)
      const anchorId = item.anchorId || (pageStart ? `pdf-page-${pageStart}` : `heading-${item.index}`)
      return activeHeading === anchorId || (!!pageStart && readerCurrentPage === pageStart)
    })
  }, [activeHeading, pdfOutlineSections, readerCurrentPage, shouldRenderHtmlPreview, tocSectionsForHtml])

  const activeCurrentSection = useMemo(() => {
    if (!shouldRenderHtmlPreview || tocSectionsForHtml.length === 0 || activeSectionIndex < 0) {
      return null
    }

    const currentSection = tocSectionsForHtml[activeSectionIndex]
    const h2Section = [...tocSectionsForHtml.slice(0, activeSectionIndex + 1)]
      .reverse()
      .find((item) => item.level === 2)

    return h2Section || currentSection || null
  }, [activeSectionIndex, shouldRenderHtmlPreview, tocSectionsForHtml])

  const showCurrentSectionIndicator =
    !!activeCurrentSection && previewScrollProgress > 6 && activeSectionIndex > 0

  const navigateBetweenSections = useCallback(
    (direction: 1 | -1) => {
      const activeSections = showingOriginalPdf ? pdfOutlineSections : tocSectionsForHtml
      if (activeSections.length === 0) {
        return
      }

      const currentIndex = activeSectionIndex >= 0 ? activeSectionIndex : 0
      const nextIndex = Math.max(0, Math.min(activeSections.length - 1, currentIndex + direction))
      const targetSection = activeSections[nextIndex]
      if (!targetSection) {
        return
      }

      if (showingOriginalPdf) {
        handlePdfTocClick(targetSection)
        return
      }

      handleReaderTocClick(targetSection)
    },
    [activeSectionIndex, handlePdfTocClick, handleReaderTocClick, pdfOutlineSections, showingOriginalPdf, tocSectionsForHtml],
  )

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) {
        return
      }

      if (event.key === 'Escape') {
        handleCloseCommentPopup()
        if (editingSection) {
          handleCloseSectionEdit()
        }
        if (showContentEditChooser) {
          handleCloseContentEditChooser()
        }
        return
      }

      if (event.metaKey || event.ctrlKey || event.altKey) {
        return
      }

      if (isTypingTarget(event.target)) {
        return
      }

      const normalizedKey = event.key.toLowerCase()
      if (normalizedKey === '/') {
        if (searchInputRef.current) {
          event.preventDefault()
          searchInputRef.current.focus()
          searchInputRef.current.select()
        }
        return
      }

      if (normalizedKey === 'j') {
        event.preventDefault()
        navigateBetweenSections(1)
        return
      }

      if (normalizedKey === 'k') {
        event.preventDefault()
        navigateBetweenSections(-1)
        return
      }

      if (normalizedKey === 'f' && onToggleFullscreen) {
        event.preventDefault()
        onToggleFullscreen()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    editingSection,
    handleCloseCommentPopup,
    handleCloseContentEditChooser,
    handleCloseSectionEdit,
    navigateBetweenSections,
    onToggleFullscreen,
    showContentEditChooser,
  ])

  // Show content if we have inline content OR attachments
  if (attachments.length === 0 && !hasInlineContent && !activeHtmlContent) {
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">??</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No Content Yet</h3>
        <p className="text-slate-500">This document has no content. Add content using the editor or upload a file.</p>
      </div>
    )
  }

  if (!activeHtmlContent && previewableAttachments.length === 0) {
    const firstAttachment = attachments[0]
    
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">??</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">Preview Not Available</h3>
        <p className="text-slate-500 mb-4">
          This document type cannot be previewed.
          <br />
          Download the file to view it.
        </p>
        {firstAttachment && (
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/documents/${documentId}/attachments/${firstAttachment.id}/download`}
            download={firstAttachment.filename}
            onClick={async (e) => {
              e.preventDefault()
              try {
                const blob = await api.getAttachmentBlob(documentId, firstAttachment.id)
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = firstAttachment.filename
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                URL.revokeObjectURL(url)
              } catch (err) {
                console.error('Download failed:', err)
              }
            }}
            className="btn-primary inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download {firstAttachment.filename}
          </a>
        )}
      </div>
    )
  }

  const documentPaperClass =
    widthMode === 'fluid'
      ? `document-preview-paper document-preview-paper-fluid ${getDocumentThemeClassName(theme)}`
      : `document-preview-paper ${getDocumentThemeClassName(theme)}`
  const effectivePdfPage = pdfOutlinePage || readerCurrentPage
  const pdfPreviewSrc = previewUrl && effectivePdfPage ? `${previewUrl}#page=${effectivePdfPage}` : previewUrl
  const pdfTocItems: PdfTocItem[] = pdfOutlineSections
    .map((item) => {
      const pageStart = resolveSectionPageStart(item)
      if (!pageStart) return null
      return {
        id: item.id,
        title: item.text,
        level: Math.max(1, item.level || 1),
        pageStart,
      }
    })
    .filter((item): item is PdfTocItem => item !== null)

  const handlePdfPreviewPanelSelect = (item: PdfTocItem) => {
    const matched = pdfOutlineSections.find((section) => section.id === item.id)
    if (matched) {
      handlePdfTocClick(matched)
      return
    }

    setPdfOutlinePage(item.pageStart)
    setReaderCurrentPage(item.pageStart)
    setActiveHeading(`pdf-page-${item.pageStart}`)
  }

  return (
    <div className="document-preview-shell surface-card rounded-2xl overflow-hidden">
      <PreviewToolbar
        previewableAttachments={previewableAttachments}
        selectedAttachment={selectedAttachment}
        onSelectAttachment={setSelectedAttachment}
        isSelectedPdf={isSelectedPdf}
        isWordDoc={isWordDoc}
        pdfPreviewMode={pdfPreviewMode}
        showingReaderView={showingReaderView}
        readerStatus={readerStatus}
        readerError={readerError}
        onSwitchToOriginalPdf={handleSwitchToOriginalPdf}
        onSwitchToReaderView={handleSwitchToReaderView}
        onRetryReaderView={handleRetryReaderView}
        fontSize={fontSize}
        onSetFontSize={handleSetFontSize}
        theme={theme}
        onSetTheme={handleSetTheme}
      />

      <div
        className={`document-current-section-indicator overflow-hidden border-b border-slate-200 bg-white transition-all duration-200 ${
          showCurrentSectionIndicator ? 'max-h-11 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        {activeCurrentSection && (
          <button
            type="button"
            onClick={() => handleReaderTocClick(activeCurrentSection)}
            className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm text-slate-600 hover:bg-sky-50 hover:text-sky-700"
            title="Current section (J/K)"
          >
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-600">
              Current section
            </span>
            <span className="flex-1 truncate font-medium text-slate-700">
              {activeCurrentSection.text}
            </span>
          </button>
        )}
      </div>

      {/* Preview area */}
      <div className="document-preview-stage relative" style={{ minHeight: '600px' }}>
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-600">{error}</p>
            </div>
          </div>
        ) : isLoading || (showingReaderView && isReaderLoading && !activeHtmlContent) ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600 mx-auto"></div>
              {showingReaderView && (
                <p className="text-xs text-slate-500 mt-3">Preparing Reader View...</p>
              )}
            </div>
          </div>
        ) : shouldRenderHtmlPreview ? (
          // Word document rendered as HTML (read-only) with TOC sidebar
          <div className="document-preview-html-layout flex h-[70vh]">
            <TocPanel
              sections={tocSectionsForHtml}
              tocCollapsed={tocCollapsed}
              onToggleCollapsed={() => setTocCollapsed((previous) => !previous)}
              activeHeading={activeHeading}
              readerCurrentPage={readerCurrentPage}
              isEditor={isEditor}
              showingReaderView={showingReaderView}
              sectionLinkBasePath={sectionLinkBasePath}
              onSectionClick={handleReaderTocClick}
              onEditSection={handleStartEditingSection}
            />

            <PreviewCanvas
              previewPaneRef={previewPaneRef}
              documentPaperClass={documentPaperClass}
              activeHtmlContent={activeHtmlContent}
              showingReaderView={showingReaderView}
              showDocumentTitle={showCanvasTitle}
              documentTitle={documentTitle}
              selectedAttachmentFilename={selectedAttachment?.filename}
              searchTerm={searchTerm}
              searchMatchCount={searchMatchCount}
              activeSearchMatchIndex={activeSearchMatchIndex}
              onSearchTermChange={setSearchTerm}
              onPreviousSearchMatch={handlePreviousSearchMatch}
              onNextSearchMatch={handleNextSearchMatch}
              searchInputRef={searchInputRef}
              tocSectionsCount={tocSectionsForHtml.length}
              readerCurrentPage={readerCurrentPage}
              isEditor={isEditor}
              commentPopupTopOffset={isFullscreen ? 76 : 0}
              scrollProgress={previewScrollProgress}
              contentStyle={contentStyle}
              sectionLinkBasePath={sectionLinkBasePath}
              onScroll={handleScroll}
              onMouseUp={handleMouseUp}
              hasUser={!!user}
              selectionPopup={selectionPopup}
              commentPopup={commentPopup}
              commentText={commentText}
              isPrivateComment={isPrivateComment}
              isSubmittingComment={isSubmittingComment}
              onOpenCommentForm={handleOpenCommentForm}
              onCloseCommentPopup={handleCloseCommentPopup}
              onCommentTextChange={setCommentText}
              onPrivateCommentChange={setIsPrivateComment}
              onSubmitComment={handleSubmitComment}
            />
          </div>
        ) : showingReaderView ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">??</div>
              <p className="text-slate-700 font-medium mb-1">Reader View is being generated</p>
              <p className="text-sm text-slate-500">
                The original PDF is available immediately. Switch back to
                <span className="font-medium text-slate-700"> View Original (PDF)</span> at any time.
              </p>
            </div>
          </div>
        ) : showingOriginalPdf && pdfPreviewUnavailableError ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-700 font-medium mb-1">
                PDF preview unavailable. Please download original.
              </p>
            </div>
          </div>
        ) : showingOriginalPdf && previewUrl ? (
          <PdfPreviewPanel
            tocItems={pdfTocItems}
            tocLoading={pdfOutlineLoading}
            tocError={pdfOutlineError}
            selectedPage={effectivePdfPage}
            onSelectItem={handlePdfPreviewPanelSelect}
            iframeSrc={pdfPreviewSrc}
            iframeKey={`${selectedAttachment?.id || 'preview'}-${effectivePdfPage || 'base'}`}
            iframeTitle="Document Preview"
            onIframeError={handlePdfIframeError}
          />
        ) : selectedAttachment && isPreviewPending(selectedAttachment) ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-600 mx-auto mb-3"></div>
              <p className="text-slate-700 font-medium mb-1">Generating PDF preview...</p>
              <p className="text-sm text-slate-500">
                The original file is preserved. Preview, TOC and Reader will appear once conversion finishes.
              </p>
            </div>
          </div>
        ) : selectedAttachment && isPreviewFailed(selectedAttachment) ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-700 font-medium mb-1">Preview PDF generation failed</p>
              <p className="text-sm text-rose-600">
                {selectedAttachment.preview_pdf_error || 'Could not build a PDF preview for this attachment.'}
              </p>
            </div>
          </div>
        ) : null}
      </div>

      {/* Download button */}
      {selectedAttachment && (
        <div className="document-preview-downloads border-t border-slate-200 p-3 bg-slate-50 flex justify-between items-center">
          <span className="text-sm text-slate-600">
            {documentTitle || selectedAttachment.filename}
            {isWordDoc(selectedAttachment) && (
              <span className="ml-2 text-xs text-sky-600">(Converted from Word)</span>
            )}
          </span>
          <div className="flex items-center gap-2">
            <a
              href={api.getAttachmentDownloadUrl(documentId, selectedAttachment.id)}
              download
              onClick={async (e) => {
                e.preventDefault()
                try {
                  const blob = await api.getAttachmentBlob(documentId, selectedAttachment.id)
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  const baseName = (documentTitle || selectedAttachment.filename || 'document').replace(
                    /\.[^/.]+$/,
                    '',
                  )
                  a.download = `${baseName}.pdf`
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                } catch (err) {
                  console.error('Download failed:', err)
                }
              }}
              className="btn-primary text-sm"
            >
              Download PDF
            </a>
            <a
              href={api.getAttachmentOriginalDownloadUrl(documentId, selectedAttachment.id)}
              className="btn-secondary text-sm"
            >
              Download Original
            </a>
          </div>
        </div>
      )}

      {/* Content Edit Chooser Popup */}
      {showContentEditChooser && (
        <ContentEditChooserPopup
          sections={tocSectionsForHtml}
          onClose={handleCloseContentEditChooser}
          onEditSection={handleChooseEditSection}
          onAddSection={handleChooseAddSection}
        />
      )}

      {/* Section Edit Popup */}
      {editingSection && (
        <SectionEditPopup
          key={`${editingSection.id}:${editingSection.editMode ?? 'edit'}`}
          documentId={documentId}
          section={editingSection}
          onClose={handleCloseSectionEdit}
          onBack={editingSection.fromChooser ? handleBackToChooser : undefined}
          onSave={handleSaveSection}
        />
      )}
    </div>
  )
}

