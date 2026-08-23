import {
  createElement,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type RefObject,
  type UIEventHandler,
} from 'react'
import { attributesToProps } from 'html-react-parser'
import { AlertTriangle, Check, ChevronDown, ChevronUp, Link2 } from 'lucide-react'
import { writeText } from '@/env/clipboard'
import { getWindowLocation } from '@/env/dom'
import type {
  CommentPopupState,
  SelectionPopupState,
} from '@/pages/document-detail/hooks/useInlineComments'
import { InlineCommentPopups } from '@/pages/document-detail/components/InlineCommentPopups'
import { parseDocumentHtml, type DocumentHtmlReplace } from '@/lib/documentRenderer'
import type { AttachmentExtractionWarning } from '@/types'

interface PreviewCanvasProps {
  previewPaneRef: RefObject<HTMLDivElement>
  documentPaperClass: string
  activeHtmlContent: string | null
  showingReaderView: boolean
  /**
   * Page-faithful PDF render. It relies on <style>, inline positioning and inline SVG,
   * all of which sanitizeHtmlForPreview strips, so it is isolated in a sandboxed iframe
   * instead of going through the normal render path.
   */
  showingFidelity?: boolean
  fidelityHtml?: string | null
  fidelityError?: string | null
  isFidelityLoading?: boolean
  showDocumentTitle?: boolean
  documentTitle?: string
  selectedAttachmentFilename?: string
  actionsBar?: ReactNode
  searchTerm: string
  searchMatchCount: number
  activeSearchMatchIndex: number
  extractionWarnings?: AttachmentExtractionWarning[]
  readerConfidence?: number | null
  onSearchTermChange: (value: string) => void
  onPreviousSearchMatch: () => void
  onNextSearchMatch: () => void
  searchInputRef: RefObject<HTMLInputElement>
  tocSectionsCount: number
  readerCurrentPage: number | null
  isEditor?: boolean
  commentPopupTopOffset?: number
  scrollProgress: number
  contentStyle?: CSSProperties
  sectionLinkBasePath: string
  onScroll: UIEventHandler<HTMLDivElement>
  hasUser: boolean
  selectionPopup: SelectionPopupState
  commentPopup: CommentPopupState
  commentText: string
  isPrivateComment: boolean
  isSubmittingComment: boolean
  onOpenCommentForm: () => void
  onCloseCommentPopup: () => void
  onCommentTextChange: (value: string) => void
  onPrivateCommentChange: (value: boolean) => void
  onSubmitComment: () => void
  isRevamp?: boolean
}

export function PreviewCanvas({
  previewPaneRef,
  documentPaperClass,
  activeHtmlContent,
  showingReaderView,
  showingFidelity = false,
  fidelityHtml = null,
  fidelityError = null,
  isFidelityLoading = false,
  showDocumentTitle = true,
  documentTitle,
  selectedAttachmentFilename,
  actionsBar,
  searchTerm,
  searchMatchCount,
  activeSearchMatchIndex,
  extractionWarnings = [],
  readerConfidence = null,
  onSearchTermChange,
  onPreviousSearchMatch,
  onNextSearchMatch,
  searchInputRef,
  tocSectionsCount,
  readerCurrentPage,
  isEditor,
  commentPopupTopOffset = 0,
  scrollProgress,
  contentStyle,
  sectionLinkBasePath,
  onScroll,
  hasUser,
  selectionPopup,
  commentPopup,
  commentText,
  isPrivateComment,
  isSubmittingComment,
  onOpenCommentForm,
  onCloseCommentPopup,
  onCommentTextChange,
  onPrivateCommentChange,
  onSubmitComment,
  isRevamp = false,
}: PreviewCanvasProps) {
  const [copiedHeadingId, setCopiedHeadingId] = useState<string | null>(null)
  const copiedHeadingTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (copiedHeadingTimeoutRef.current !== null) {
        window.clearTimeout(copiedHeadingTimeoutRef.current)
      }
    }
  }, [])

  const handleCopyHeadingLink = useCallback(async (anchorId: string) => {
    const sectionUrl = new URL(sectionLinkBasePath, getWindowLocation().origin)
    sectionUrl.hash = anchorId

    try {
      await writeText(sectionUrl.toString())
      setCopiedHeadingId(anchorId)
      if (copiedHeadingTimeoutRef.current !== null) {
        window.clearTimeout(copiedHeadingTimeoutRef.current)
      }
      copiedHeadingTimeoutRef.current = window.setTimeout(() => setCopiedHeadingId(null), 1600)
    } catch {
      setCopiedHeadingId(null)
    }
  }, [sectionLinkBasePath])

  const renderedContent = useMemo(() => {
    const replace: DocumentHtmlReplace = (domNode, _index, context) => {
      if (
        domNode.type !== 'tag' ||
        (domNode.name !== 'p' && !/^h[1-6]$/.test(domNode.name))
      ) {
        return undefined
      }

      const anchorId = domNode.attribs.id
      const isAnchorHeading = /^h[1-3]$/.test(domNode.name) && typeof anchorId === 'string'
      const headingChildren = isAnchorHeading
        ? [
            createElement(
              'button',
              {
                key: `${anchorId}-copy-link`,
                type: 'button',
                className: 'document-heading-anchor',
                'aria-label': `Copy link to ${anchorId}`,
                onMouseUp: (event) => {
                  event.stopPropagation()
                },
                onClick: (event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  void handleCopyHeadingLink(anchorId)
                },
              },
              copiedHeadingId === anchorId ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <Link2 className="h-3.5 w-3.5" />
              ),
            ),
            createElement(
              'span',
              {
                key: `${anchorId}-content`,
                className: 'document-heading-anchor-content',
              },
              context.renderChildren(domNode.children as unknown as import('html-react-parser').DOMNode[]),
            ),
          ]
        : context.renderChildren(domNode.children as unknown as import('html-react-parser').DOMNode[])

      return createElement(
        domNode.name,
        {
          ...attributesToProps(domNode.attribs),
          className: [
            domNode.attribs.class,
            isAnchorHeading ? 'document-heading-copyable group' : undefined,
          ]
            .filter(Boolean)
            .join(' '),
        },
        headingChildren,
      )
    }

    return parseDocumentHtml(activeHtmlContent || '', { replace })
  }, [activeHtmlContent, copiedHeadingId, handleCopyHeadingLink])

  const headerTitle = documentTitle || selectedAttachmentFilename
  const hasSearchTerm = searchTerm.trim().length > 0
  const searchCountLabel = searchMatchCount > 0 ? `${activeSearchMatchIndex + 1} of ${searchMatchCount}` : '0 of 0'
  const visibleWarnings = extractionWarnings.filter((warning) => warning.message.trim().length > 0)

  return (
    <div className="document-preview-canvas flex-1 flex flex-col overflow-hidden">
      <div
        className={`document-preview-topbar text-white flex flex-col gap-2 px-4 flex-shrink-0 md:flex-row md:items-center md:justify-between ${
          isRevamp
            ? 'border-b border-blue-800/50 bg-gradient-to-r from-blue-800 via-blue-700 to-blue-600 py-2.5'
            : 'bg-gradient-to-r from-blue-600 to-blue-700 py-2'
        }`}
      >
        {showDocumentTitle && headerTitle ? (
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
            </svg>
            <span className="font-medium truncate">{headerTitle}</span>
          </div>
        ) : (
          <div />
        )}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <input
              ref={searchInputRef}
              type="text"
              value={searchTerm}
              onChange={(event) => onSearchTermChange(event.target.value)}
              placeholder="Search in document"
              title="Search in document (/)"
              aria-label="Search in document"
              className="w-44 md:w-56 rounded-lg bg-white/15 text-white placeholder:text-white/70 border border-white/20 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-white/40"
            />
          </div>
          {hasSearchTerm && (
            <>
              <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
                {searchCountLabel}
              </span>
              <div className="inline-flex overflow-hidden rounded-lg border border-white/20">
                <button
                  type="button"
                  onClick={onPreviousSearchMatch}
                  disabled={searchMatchCount === 0}
                  className="px-2 py-1 text-white hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
                  title="Previous match"
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={onNextSearchMatch}
                  disabled={searchMatchCount === 0}
                  className="border-l border-white/20 px-2 py-1 text-white hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
                  title="Next match"
                >
                  <ChevronDown className="h-3.5 w-3.5" />
                </button>
              </div>
            </>
          )}
          {tocSectionsCount > 0 && (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded">{tocSectionsCount} sections</span>
          )}
          {showingReaderView && readerCurrentPage && (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
              Page {readerCurrentPage}
            </span>
          )}
          {isEditor && !showingReaderView && !showingFidelity ? (
            <span className="text-xs bg-emerald-500/80 px-2 py-0.5 rounded whitespace-nowrap">
              Click section to edit
            </span>
          ) : (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
              {showingFidelity ? 'Original Layout' : showingReaderView ? 'Reader View' : 'Read Only'}
            </span>
          )}
        </div>
      </div>
      {actionsBar ? (
        <div
          className={`border-b border-slate-200 px-3 py-2 ${
            isRevamp ? 'bg-white/95' : 'bg-slate-100/95'
          }`}
        >
          {actionsBar}
        </div>
      ) : null}

      {visibleWarnings.length > 0 && (
        <div className="document-extraction-banner" role="status" aria-live="polite">
          <div className="document-extraction-banner__icon">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="document-extraction-banner__body">
            <p className="document-extraction-banner__title">
              Some document elements were only partially extracted.
            </p>
            <p className="document-extraction-banner__details">
              {visibleWarnings.map((warning) => warning.message).join(' ')}
              {readerConfidence !== null ? ` Extraction confidence: ${Math.round(readerConfidence * 100)}%.` : ''}
            </p>
          </div>
        </div>
      )}

      <div
        ref={previewPaneRef}
        // In fidelity mode the render is an absolutely positioned overlay, so nothing is
        // left in flow for this region to take its height from and it collapses to the
        // progress bar. Every other mode is sized by the paper it contains.
        className={`document-preview-scroll-region flex-1 relative document-preview-pane ${
          showingFidelity ? 'overflow-hidden min-h-[70vh]' : 'overflow-y-auto overflow-x-auto'
        }`}
        onScroll={onScroll}
      >
        <div className="document-reading-progress z-10 h-[3px]" aria-hidden="true">
          <div
            data-testid="document-reading-progress-bar"
            className="document-reading-progress__bar h-full bg-blue-700 transition-[width] duration-150 ease-out"
            style={{ width: `${scrollProgress}%` }}
          />
        </div>

        {showingFidelity ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
            {fidelityHtml ? (
              <iframe
                title="Original page layout"
                data-testid="document-fidelity-frame"
                srcDoc={fidelityHtml}
                // Fully restricted: the render is static markup, CSS and embedded fonts.
                sandbox=""
                className="h-full w-full border-0"
              />
            ) : isFidelityLoading ? (
              <p className="helper-copy">Rendering the original layout...</p>
            ) : (
              <p className="helper-copy text-amber-700">
                {fidelityError || 'Original layout is unavailable for this attachment.'}
              </p>
            )}
          </div>
        ) : (
          <div className={documentPaperClass} data-testid="document-preview-paper">
            <div
              id="document-content-area"
              data-tour="document-inline-comment-area"
              className={`document-preview-content ${
                showingReaderView ? 'document-preview-content--reader' : ''
              }`}
              style={contentStyle}
            >
              {renderedContent}
            </div>
          </div>
        )}

        <InlineCommentPopups
          hasUser={hasUser}
          selectionPopup={selectionPopup}
          commentPopup={commentPopup}
          commentText={commentText}
          isPrivateComment={isPrivateComment}
          isSubmittingComment={isSubmittingComment}
          topOffset={commentPopupTopOffset}
          onOpenCommentForm={onOpenCommentForm}
          onCloseCommentPopup={onCloseCommentPopup}
          onCommentTextChange={onCommentTextChange}
          onPrivateCommentChange={onPrivateCommentChange}
          onSubmitComment={onSubmitComment}
        />
      </div>
    </div>
  )
}
