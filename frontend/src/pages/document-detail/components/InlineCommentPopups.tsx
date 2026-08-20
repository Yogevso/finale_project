import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Loader2, Lock, MessageSquarePlus, Send, X } from 'lucide-react'
import type {
  CommentPopupState,
  SelectionPopupState,
} from '@/pages/document-detail/hooks/useInlineComments'

/** Breathing room kept between the popup and the viewport edges. */
const VIEWPORT_MARGIN = 12
/** Gap between the selected text and the popup placed against it. */
const ANCHOR_GAP = 12
/** Keeps the arrow clear of the card's rounded corners when the card is clamped. */
const ARROW_INSET = 20

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
  const commentPopupRef = useRef<HTMLDivElement | null>(null)
  // w-80; replaced with the real box as soon as the popup is on screen.
  const [popupSize, setPopupSize] = useState({ width: 320, height: 0 })
  const [viewport, setViewport] = useState(() => ({
    width: typeof window === 'undefined' ? 0 : window.innerWidth,
    height: typeof window === 'undefined' ? 0 : window.innerHeight,
  }))

  useLayoutEffect(() => {
    const node = commentPopupRef.current
    if (!commentPopup.show || !node) {
      return
    }

    const measure = () => {
      const rect = node.getBoundingClientRect()
      setPopupSize((current) =>
        current.width === rect.width && current.height === rect.height
          ? current
          : { width: rect.width, height: rect.height },
      )
    }

    const readViewport = () => {
      setViewport((current) =>
        current.width === window.innerWidth && current.height === window.innerHeight
          ? current
          : { width: window.innerWidth, height: window.innerHeight },
      )
    }

    measure()
    readViewport()

    // The quoted text and the textarea can reflow after the first paint.
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure)
    observer?.observe(node)

    const handleResize = () => {
      readViewport()
      measure()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', handleResize)
    }
  }, [commentPopup.show])

  const commentPlacement = useMemo(() => {
    const viewportWidth = viewport.width || window.innerWidth
    const viewportHeight = viewport.height || window.innerHeight
    const halfWidth = popupSize.width / 2

    // Horizontal: keep the whole card on screen. The arrow re-aims at the selection below.
    const minLeft = VIEWPORT_MARGIN + halfWidth
    const maxLeft = viewportWidth - VIEWPORT_MARGIN - halfWidth
    const left =
      maxLeft < minLeft
        ? viewportWidth / 2
        : Math.min(Math.max(commentPopup.x, minLeft), maxLeft)

    // Vertical: sit under the selection, and flip above it when the bottom would be cut off.
    const anchorTop = commentPopup.anchorTop ?? commentPopup.y
    const anchorBottom = commentPopup.anchorBottom ?? commentPopup.y
    const minTop = topOffset + VIEWPORT_MARGIN
    const maxTop = viewportHeight - VIEWPORT_MARGIN - popupSize.height

    let top = anchorBottom + ANCHOR_GAP
    let isAbove = false

    if (popupSize.height > 0 && top > maxTop) {
      const flippedTop = anchorTop - ANCHOR_GAP - popupSize.height
      if (flippedTop >= minTop) {
        top = flippedTop
        isAbove = true
      } else {
        top = Math.max(maxTop, minTop)
      }
    }

    return {
      left,
      top: Math.max(top, minTop),
      isAbove,
      arrowOffset: Math.min(
        Math.max(commentPopup.x - left, -halfWidth + ARROW_INSET),
        halfWidth - ARROW_INSET,
      ),
    }
  }, [
    commentPopup.anchorBottom,
    commentPopup.anchorTop,
    commentPopup.x,
    commentPopup.y,
    popupSize.height,
    popupSize.width,
    topOffset,
    viewport.height,
    viewport.width,
  ])

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
          ref={commentPopupRef}
          className="inline-comment-popup fixed z-50 -translate-x-1/2 transform"
          style={{
            left: commentPlacement.left,
            top: commentPlacement.top,
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

          <div
            className={`absolute left-1/2 ${commentPlacement.isAbove ? '-bottom-2' : '-top-2'}`}
            style={{ transform: `translateX(calc(-50% + ${commentPlacement.arrowOffset}px))` }}
          >
            <div
              className={`h-0 w-0 border-l-8 border-r-8 border-transparent ${
                commentPlacement.isAbove
                  ? 'border-t-8 border-t-white'
                  : 'border-b-8 border-b-amber-50'
              }`}
            />
          </div>
        </div>
      ) : null}
    </>
  )
}
