import { Loader2, Lock, Send, X } from 'lucide-react'
import type {
  CommentPopupState,
  SelectionPopupState,
} from '@/pages/document-detail/hooks/useInlineComments'

interface InlineCommentPopupsProps {
  hasUser: boolean
  selectionPopup: SelectionPopupState
  commentPopup: CommentPopupState
  commentText: string
  isPrivateComment: boolean
  isSubmittingComment: boolean
  topOffset?: number
  onOpenCommentForm: () => void
  onCloseCommentPopup: () => void
  onCommentTextChange: (value: string) => void
  onPrivateCommentChange: (value: boolean) => void
  onSubmitComment: () => void
}

export function InlineCommentPopups({
  hasUser,
  selectionPopup,
  commentPopup,
  commentText,
  isPrivateComment,
  isSubmittingComment,
  topOffset = 0,
  onOpenCommentForm,
  onCloseCommentPopup,
  onCommentTextChange,
  onPrivateCommentChange,
  onSubmitComment,
}: InlineCommentPopupsProps) {
  return (
    <>
      {selectionPopup.show && !commentPopup.show && (
        <div
          className="fixed z-50 transform -translate-x-1/2 -translate-y-full"
          style={{ left: selectionPopup.x, top: Math.max(selectionPopup.y, topOffset + 12) }}
        >
          <button
            onClick={onOpenCommentForm}
            className="flex items-center gap-1 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full shadow-lg hover:bg-amber-600 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            Add Comment
          </button>
          <div className="absolute left-1/2 transform -translate-x-1/2 top-full">
            <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-amber-500"></div>
          </div>
        </div>
      )}

      {commentPopup.show && hasUser && (
        <div
          className="inline-comment-popup fixed z-50 transform -translate-x-1/2"
          style={{
            left: Math.max(180, Math.min(commentPopup.x, window.innerWidth - 180)),
            top: Math.max(commentPopup.y, topOffset + 24),
          }}
        >
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-80 overflow-hidden">
            <div className="bg-amber-50 border-b border-amber-100 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-amber-800 mb-1">Commenting on:</p>
                  <p className="text-sm text-amber-700 italic line-clamp-2">
                    "{commentPopup.text.slice(0, 100)}
                    {commentPopup.text.length > 100 ? '...' : ''}"
                  </p>
                </div>
                <button
                  onClick={onCloseCommentPopup}
                  className="p-1 hover:bg-amber-100 rounded text-amber-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="p-4 space-y-3">
              <textarea
                value={commentText}
                onChange={(event) => onCommentTextChange(event.target.value)}
                placeholder="Write your comment..."
                className="input-field resize-none"
                rows={3}
                autoFocus
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                    onSubmitComment()
                  }
                  if (event.key === 'Escape') {
                    onCloseCommentPopup()
                  }
                }}
              />

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isPrivateComment}
                    onChange={(event) => onPrivateCommentChange(event.target.checked)}
                    className="rounded border-slate-300 text-amber-500 focus:ring-amber-500"
                  />
                  <span className="flex items-center gap-1">
                    <Lock className="h-3.5 w-3.5" />
                    Private
                  </span>
                </label>

                <div className="flex items-center gap-2">
                  <button onClick={onCloseCommentPopup} className="btn-ghost text-sm">
                    Cancel
                  </button>
                  <button
                    onClick={onSubmitComment}
                    disabled={!commentText.trim() || isSubmittingComment}
                    className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    {isSubmittingComment ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Posting...
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        Post
                      </>
                    )}
                  </button>
                </div>
              </div>

              <p className="text-xs text-slate-400 text-center">
                Press Ctrl+Enter to submit | Esc to cancel
              </p>
            </div>
          </div>

          <div className="absolute left-1/2 transform -translate-x-1/2 -top-2">
            <div className="w-0 h-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-white"></div>
          </div>
        </div>
      )}
    </>
  )
}
