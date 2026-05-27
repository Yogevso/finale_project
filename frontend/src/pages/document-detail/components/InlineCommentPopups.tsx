import { Loader2, Lock, MessageSquarePlus, Send, X } from 'lucide-react'
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
  showPrivateOption?: boolean
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
  showPrivateOption = true,
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
      {selectionPopup.show && !commentPopup.show ? (
        <div
          className="fixed z-50 -translate-x-1/2 -translate-y-full transform"
          style={{ left: selectionPopup.x, top: Math.max(selectionPopup.y, topOffset + 12) }}
        >
          <button
            type="button"
            onClick={onOpenCommentForm}
            className="btn-warning table-action-btn inline-flex items-center gap-1 shadow-lg"
          >
            <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
            Add Comment
          </button>
          <div className="absolute left-1/2 top-full -translate-x-1/2 transform">
            <div className="h-0 w-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-amber-500" />
          </div>
        </div>
      ) : null}

      {commentPopup.show && hasUser ? (
        <div
          className="inline-comment-popup fixed z-50 -translate-x-1/2 transform"
          style={{
            left: Math.max(180, Math.min(commentPopup.x, window.innerWidth - 180)),
            top: Math.max(commentPopup.y, topOffset + 24),
          }}
        >
          <div className="surface-card w-80 overflow-hidden rounded-2xl shadow-2xl">
            <div className="border-b border-amber-100 bg-amber-50 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="helper-copy mb-1 font-medium uppercase tracking-wide text-amber-800">
                    Commenting on
                  </p>
                  <p className="body-copy line-clamp-2 italic text-amber-700">
                    "{commentPopup.text.slice(0, 100)}
                    {commentPopup.text.length > 100 ? '...' : ''}"
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onCloseCommentPopup}
                  className="btn-icon h-8 w-8 border-0 bg-transparent text-amber-600 hover:bg-amber-100 hover:text-amber-800"
                  aria-label="Close comment popup"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-3 p-4">
              <textarea
                value={commentText}
                onChange={(event) => onCommentTextChange(event.target.value)}
                placeholder="Write your comment..."
                className="input-field resize-none"
                rows={3}
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
                {showPrivateOption ? (
                  <label className="body-copy flex cursor-pointer items-center gap-2">
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
                ) : (
                  <span />
                )}

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onCloseCommentPopup}
                    className="btn-ghost table-action-btn"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={onSubmitComment}
                    disabled={!commentText.trim() || isSubmittingComment}
                    className="btn-warning table-action-btn flex items-center gap-1 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isSubmittingComment ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Posting...
                      </>
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5" />
                        Post
                      </>
                    )}
                  </button>
                </div>
              </div>

              <p className="helper-copy text-center">Press Ctrl+Enter to submit | Esc to cancel</p>
            </div>
          </div>

          <div className="absolute left-1/2 -top-2 -translate-x-1/2 transform">
            <div className="h-0 w-0 border-l-8 border-r-8 border-b-8 border-transparent border-b-white" />
          </div>
        </div>
      ) : null}
    </>
  )
}
