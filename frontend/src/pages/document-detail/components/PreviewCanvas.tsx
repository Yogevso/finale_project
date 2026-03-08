import type { MouseEventHandler, RefObject, UIEventHandler } from 'react'
import type {
  CommentPopupState,
  SelectionPopupState,
} from '@/pages/document-detail/hooks/useInlineComments'
import { InlineCommentPopups } from '@/pages/document-detail/components/InlineCommentPopups'

interface PreviewCanvasProps {
  previewPaneRef: RefObject<HTMLDivElement>
  documentPaperClass: string
  activeHtmlContent: string | null
  showingReaderView: boolean
  documentTitle?: string
  selectedAttachmentFilename?: string
  searchTerm: string
  onSearchTermChange: (value: string) => void
  tocSectionsCount: number
  readerCurrentPage: number | null
  isEditor?: boolean
  onScroll: UIEventHandler<HTMLDivElement>
  onMouseUp: MouseEventHandler<HTMLDivElement>
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
}

export function PreviewCanvas({
  previewPaneRef,
  documentPaperClass,
  activeHtmlContent,
  showingReaderView,
  documentTitle,
  selectedAttachmentFilename,
  searchTerm,
  onSearchTermChange,
  tocSectionsCount,
  readerCurrentPage,
  isEditor,
  onScroll,
  onMouseUp,
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
}: PreviewCanvasProps) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="bg-gradient-to-r from-sky-600 to-sky-700 text-white px-4 py-2 flex flex-col gap-2 md:flex-row md:items-center md:justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
          </svg>
          <span className="font-medium truncate">{documentTitle || selectedAttachmentFilename}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(event) => onSearchTermChange(event.target.value)}
              placeholder="Search in document"
              className="w-44 md:w-56 rounded-lg bg-white/15 text-white placeholder:text-white/70 border border-white/20 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-white/40"
            />
          </div>
          {tocSectionsCount > 0 && (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded">{tocSectionsCount} sections</span>
          )}
          {showingReaderView && readerCurrentPage && (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
              Page {readerCurrentPage}
            </span>
          )}
          {isEditor && !showingReaderView ? (
            <span className="text-xs bg-emerald-500/80 px-2 py-0.5 rounded whitespace-nowrap">
              Click section to edit
            </span>
          ) : (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded whitespace-nowrap">
              {showingReaderView ? 'Reader View' : 'Read Only'}
            </span>
          )}
        </div>
      </div>

      <div
        ref={previewPaneRef}
        className="flex-1 relative overflow-y-auto overflow-x-hidden document-preview-pane"
        onScroll={onScroll}
      >
        <div className={documentPaperClass}>
          <div
            id="document-content-area"
            data-tour="document-inline-comment-area"
            className={`document-preview-content ${
              showingReaderView ? 'document-preview-content--reader' : ''
            }`}
            dangerouslySetInnerHTML={{ __html: activeHtmlContent || '' }}
            onMouseUp={onMouseUp}
          />
        </div>

        <InlineCommentPopups
          hasUser={hasUser}
          selectionPopup={selectionPopup}
          commentPopup={commentPopup}
          commentText={commentText}
          isPrivateComment={isPrivateComment}
          isSubmittingComment={isSubmittingComment}
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
