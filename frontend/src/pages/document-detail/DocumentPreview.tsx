import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { getDocument, getDomParser } from '@/env/dom'
import { api } from '@/lib/api'
import { useAttachmentDownload } from '@/hooks/useAttachmentDownload'
import { useAuth } from '@/lib/auth'
import type { CSSProperties } from 'react'
import type { ReadingWidth } from '@/lib/readingWidth'
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
import { usePreviewProgress } from '@/pages/document-detail/hooks/usePreviewProgress'
import { usePreviewShortcuts } from '@/pages/document-detail/hooks/usePreviewShortcuts'
import { usePreviewSource } from '@/pages/document-detail/hooks/usePreviewSource'
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

const WORDS_PER_MINUTE = 200

function estimateReadingTimeMinutes(html: string | null): number | null {
  if (!html) {
    return null
  }

  const textContent = getDomParser().parseFromString(html, 'text/html').body.textContent ?? ''
  const wordCount = textContent.trim().split(/\s+/).filter(Boolean).length

  if (wordCount === 0) {
    return null
  }

  return Math.max(1, Math.ceil(wordCount / WORDS_PER_MINUTE))
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
  const [htmlContent, setHtmlContent] = useState<string | null>(null)
  const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [sections, setSections] = useState<TocSection[]>([])
  const [tocCollapsed, setTocCollapsed] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchMatchCount, setSearchMatchCount] = useState(0)
  const [activeSearchMatchIndex, setActiveSearchMatchIndex] = useState(-1)
  const [fontSize, setFontSizeState] = useState<DocumentFontSize>(() => getDocumentFontSize())
  const [theme, setThemeState] = useState<DocumentTheme>(() => getDocumentTheme())
  const { downloadAttachment } = useAttachmentDownload(documentId)
  const previewPaneRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
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

  const handleSetFontSize = useCallback((value: DocumentFontSize) => {
    setFontSizeState(value)
    setDocumentFontSize(value)
  }, [])

  const handleSetTheme = useCallback((value: DocumentTheme) => {
    setThemeState(value)
    setDocumentTheme(value)
  }, [])

  const processHtmlWithSections = useCallback((html: string) => {
    const processed = processHtmlIntoSections(html)
    setSections(processed.sections)
    return processed.html
  }, [])

  const {
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
  } = useReaderView({
    documentId,
    selectedAttachment,
    sections,
    setSections,
    processHtmlWithSections,
  })

  const {
    previewableAttachments,
    activeHtmlContent,
    showingReaderView,
    shouldRenderHtmlPreview,
    previewState,
  } = usePreviewSource({
    attachments,
    selectedAttachment,
    setSelectedAttachment,
    inlineContent: htmlContent,
    readerHtmlContent,
    readerStatus,
  })

  const contentStyle = useMemo(
    () =>
      ({
        '--doc-font-size': DOCUMENT_FONT_SIZE_VALUES[fontSize],
      }) as CSSProperties,
    [fontSize],
  )

  const focusSearchMatch = useCallback((targetIndex: number, behavior: ScrollBehavior = 'smooth') => {
    const container = getDocument().getElementById('document-content-area')
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
    showingReaderView: selectedAttachment !== null,
    activeHtmlContent: htmlContent,
    isLoading,
    sections,
    applyProcessedHtml,
    onRequireInlineContent: () => setSelectedAttachment(null),
  })

  const { previewScrollProgress, handleScroll } = usePreviewProgress({
    documentId,
    activeHtmlContent,
    selectedAttachmentId: selectedAttachment?.id ?? null,
    previewPaneRef,
    activeHeading,
    setActiveHeading,
    sections,
    readerCurrentPage,
    setReaderCurrentPage,
    onScrollProgress,
    hasUser: !!user,
  })

  useEffect(() => {
    const container = getDocument().getElementById('document-content-area')
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
    const loadInlineContent = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const versionsResponse = await api.getVersions(documentId)
        const withContent = versionsResponse.items.filter((version) =>
          Boolean(getUsableVersionContent(version.content)),
        )
        const publishedVersion = withContent
          .filter((version) => version.is_published)
          .sort(
            (left, right) =>
              new Date(right.published_at || right.created_at).getTime() -
              new Date(left.published_at || left.created_at).getTime(),
          )[0]
        const latestVersion = withContent.sort(
          (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
        )[0]
        let versionToShow = publishedVersion || latestVersion

        if (!versionToShow && versionsResponse.items.length > 0) {
          const prioritizedIds = [
            ...new Set([
              ...versionsResponse.items
                .filter((version) => version.is_published)
                .sort(
                  (left, right) =>
                    new Date(right.published_at || right.created_at).getTime() -
                    new Date(left.published_at || left.created_at).getTime(),
                )
                .map((version) => version.id),
              ...versionsResponse.items
                .sort(
                  (left, right) =>
                    new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
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
          setHtmlContent(processHtmlWithSections(versionContent))
        } else {
          setHtmlContent(null)
          if (!selectedAttachment) {
            setSections([])
          }
        }
      } catch (loadError) {
        console.error('Preview load error:', loadError)
        setError('Failed to load preview')
        setHtmlContent(null)
        setSections([])
      } finally {
        setIsLoading(false)
      }
    }

    void loadInlineContent()
  }, [documentId, processHtmlWithSections, selectedAttachment, setSections])

  const tocSectionsForHtml = sections

  const handleReaderTocClick = useCallback(
    (item: TocSection) => {
      navigateReaderToSection(item, 'smooth')
    },
    [navigateReaderToSection],
  )

  const activeSectionIndex = useMemo(() => {
    if (tocSectionsForHtml.length === 0) {
      return -1
    }

    return tocSectionsForHtml.findIndex((item) => {
      const pageStart = resolveSectionPageStart(item)
      const anchorId = item.anchorId || `heading-${item.index}`
      return activeHeading === anchorId || (!!pageStart && readerCurrentPage === pageStart)
    })
  }, [activeHeading, readerCurrentPage, tocSectionsForHtml])

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
      if (tocSectionsForHtml.length === 0) {
        return
      }

      const currentIndex = activeSectionIndex >= 0 ? activeSectionIndex : 0
      const nextIndex = Math.max(0, Math.min(tocSectionsForHtml.length - 1, currentIndex + direction))
      const targetSection = tocSectionsForHtml[nextIndex]
      if (!targetSection) {
        return
      }

      handleReaderTocClick(targetSection)
    },
    [activeSectionIndex, handleReaderTocClick, tocSectionsForHtml],
  )

  usePreviewShortcuts({
    searchInputRef,
    editingSection,
    showContentEditChooser,
    handleCloseCommentPopup,
    handleCloseContentEditChooser,
    handleCloseSectionEdit,
    navigateBetweenSections,
    onToggleFullscreen,
  })

  if (previewState === 'NO_CONTENT') {
    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">??</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No Content Yet</h3>
        <p className="text-slate-500">This document has no content. Add content using the editor or upload a file.</p>
      </div>
    )
  }

  if (previewState === 'DOWNLOAD_ONLY') {
    const firstAttachment = attachments[0] ?? null

    return (
      <div className="surface-card rounded-2xl p-12 text-center">
        <div className="text-6xl mb-4">??</div>
        <h3 className="text-lg font-display font-medium text-slate-900 mb-2">Preview Not Available</h3>
        <p className="text-slate-500 mb-4">
          This attachment can be downloaded, but it cannot be previewed inline.
          <br />
          Download the original file to view it.
        </p>
        {firstAttachment && (
          <a
            href={api.getAttachmentDownloadUrl(documentId, firstAttachment.id)}
            download={firstAttachment.filename}
            onClick={(event) => {
              event.preventDefault()
              void downloadAttachment(firstAttachment)
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

  return (
    <div className="document-preview-shell surface-card rounded-2xl overflow-hidden">
      <PreviewToolbar
        previewableAttachments={previewableAttachments}
        selectedAttachment={selectedAttachment}
        onSelectAttachment={setSelectedAttachment}
        readerError={readerError}
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

      <div className="document-preview-stage relative" style={{ minHeight: '600px' }}>
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-600">{error}</p>
            </div>
          </div>
        ) : previewState === 'LOADING' || isLoading || (selectedAttachment && isReaderLoading && !activeHtmlContent) ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-600 mx-auto"></div>
              {selectedAttachment && (
                <p className="text-xs text-slate-500 mt-3">Preparing document preview...</p>
              )}
            </div>
          </div>
        ) : previewState === 'READY' && shouldRenderHtmlPreview ? (
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
              extractionWarnings={readerWarnings}
              readerConfidence={readerConfidence}
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
        ) : previewState === 'ERROR' && selectedAttachment && readerError ? (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="text-center max-w-lg">
              <div className="text-4xl mb-2">??</div>
              <p className="text-rose-700 font-medium mb-1">Preview unavailable</p>
              <p className="text-sm text-rose-600">{readerError}</p>
            </div>
          </div>
        ) : null}
      </div>

      {selectedAttachment && (
        <div className="document-preview-downloads border-t border-slate-200 p-3 bg-slate-50 flex justify-between items-center">
          <span className="text-sm text-slate-600">
            {documentTitle || selectedAttachment.filename}
          </span>
          <a
            href={api.getAttachmentDownloadUrl(documentId, selectedAttachment.id)}
            download
            onClick={(event) => {
              event.preventDefault()
              void downloadAttachment(selectedAttachment)
            }}
            className="btn-primary text-sm"
          >
            Download Original
          </a>
        </div>
      )}

      {showContentEditChooser && (
        <ContentEditChooserPopup
          sections={tocSectionsForHtml}
          onClose={handleCloseContentEditChooser}
          onEditSection={handleChooseEditSection}
          onAddSection={handleChooseAddSection}
        />
      )}

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
