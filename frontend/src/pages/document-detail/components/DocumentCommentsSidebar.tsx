import { useMemo, useState } from 'react'
import { CheckCircle2, Eye, EyeOff, MessageSquareText, RotateCcw, Send } from 'lucide-react'
import type { Comment } from '@/types'

interface DocumentCommentsSidebarProps {
  threads: Comment[]
  isLoading: boolean
  isError: boolean
  showResolved: boolean
  activeThreadId: number | null
  canResolveThreads: boolean
  resolveMutationPending: boolean
  submittingReplyThreadId: number | null
  onToggleShowResolved: (next: boolean) => void
  onThreadSelect: (threadId: number) => void
  onToggleThreadResolved: (threadId: number, resolve: boolean) => void
  onSubmitReply: (threadId: number, content: string) => void
}

function getCommentAuthorName(comment: Comment): string {
  return comment.author_name || comment.user?.full_name || comment.user?.username || 'Unknown user'
}

function formatTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function renderNestedReplies(comment: Comment, depth: number = 1): JSX.Element[] {
  const replies = comment.replies || []
  if (replies.length === 0) {
    return []
  }

  return replies.flatMap((reply) => {
    const node = (
      <div
        key={reply.id}
        className={`rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 ${
          depth > 1 ? 'ml-3' : ''
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold text-slate-700">{getCommentAuthorName(reply)}</p>
          <p className="text-[11px] text-slate-500">{formatTimestamp(reply.created_at)}</p>
        </div>
        <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{reply.content}</p>
      </div>
    )
    return [node, ...renderNestedReplies(reply, depth + 1)]
  })
}

export function DocumentCommentsSidebar({
  threads,
  isLoading,
  isError,
  showResolved,
  activeThreadId,
  canResolveThreads,
  resolveMutationPending,
  submittingReplyThreadId,
  onToggleShowResolved,
  onThreadSelect,
  onToggleThreadResolved,
  onSubmitReply,
}: DocumentCommentsSidebarProps) {
  const [replyDrafts, setReplyDrafts] = useState<Record<number, string>>({})

  const visibleThreads = useMemo(
    () => (showResolved ? threads : threads.filter((thread) => !thread.is_resolved)),
    [showResolved, threads],
  )

  const openCount = useMemo(
    () => threads.filter((thread) => !thread.is_resolved).length,
    [threads],
  )

  return (
    <aside className="document-comments-sidebar flex w-full flex-col border-t border-slate-200 bg-white md:w-[21rem] md:min-w-[19rem] md:max-w-[24rem] md:border-l md:border-t-0">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Comments
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {openCount} open thread{openCount === 1 ? '' : 's'}
          </p>
        </div>
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-slate-600">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(event) => onToggleShowResolved(event.target.checked)}
            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          {showResolved ? (
            <>
              <Eye className="h-3.5 w-3.5" />
              Resolved
            </>
          ) : (
            <>
              <EyeOff className="h-3.5 w-3.5" />
              Resolved
            </>
          )}
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {isLoading ? <p className="text-sm text-slate-500">Loading comments...</p> : null}
        {isError ? (
          <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            Failed to load comments.
          </p>
        ) : null}
        {!isLoading && !isError && visibleThreads.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-center">
            <MessageSquareText className="mx-auto h-5 w-5 text-slate-400" />
            <p className="mt-2 text-sm font-medium text-slate-700">No visible threads</p>
            <p className="mt-1 text-xs text-slate-500">
              Select text in the document to add the first comment.
            </p>
          </div>
        ) : null}

        <div className="space-y-3">
          {visibleThreads.map((thread) => {
            const replyDraft = replyDrafts[thread.id] || ''
            const isSubmittingReply = submittingReplyThreadId === thread.id

            return (
              <article
                key={thread.id}
                data-thread-id={thread.id}
                className={`rounded-2xl border px-3 py-3 transition ${
                  activeThreadId === thread.id
                    ? 'border-blue-300 bg-blue-50/70 shadow-sm'
                    : 'border-slate-200 bg-white'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onThreadSelect(thread.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-semibold text-slate-800">
                      {getCommentAuthorName(thread)}
                    </p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        thread.is_resolved
                          ? 'border border-emerald-200 bg-emerald-50 text-emerald-700'
                          : 'border border-amber-200 bg-amber-50 text-amber-700'
                      }`}
                    >
                      {thread.is_resolved ? 'Resolved' : 'Open'}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500">{formatTimestamp(thread.created_at)}</p>
                  {thread.anchor_text ? (
                    <p className="mt-2 line-clamp-2 text-xs italic text-slate-500">
                      "{thread.anchor_text}"
                    </p>
                  ) : null}
                  <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{thread.content}</p>
                </button>

                <div className="mt-3 flex items-center gap-2">
                  {canResolveThreads ? (
                    <button
                      type="button"
                      disabled={resolveMutationPending}
                      onClick={() => onToggleThreadResolved(thread.id, !thread.is_resolved)}
                      className="inline-flex items-center gap-1 rounded-full border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {thread.is_resolved ? (
                        <>
                          <RotateCcw className="h-3.5 w-3.5" />
                          Reopen
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Resolve
                        </>
                      )}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => onThreadSelect(thread.id)}
                    className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-100"
                  >
                    Jump to text
                  </button>
                </div>

                {thread.replies.length > 0 ? (
                  <div className="mt-3 space-y-2">{renderNestedReplies(thread)}</div>
                ) : null}

                <div className="mt-3 space-y-2">
                  <textarea
                    value={replyDraft}
                    onChange={(event) =>
                      setReplyDrafts((previous) => ({
                        ...previous,
                        [thread.id]: event.target.value,
                      }))
                    }
                    placeholder="Write a reply..."
                    rows={2}
                    className="input-field resize-none"
                  />
                  <div className="flex justify-end">
                    <button
                      type="button"
                      disabled={!replyDraft.trim() || isSubmittingReply}
                      onClick={() => {
                        const value = replyDraft.trim()
                        if (!value) {
                          return
                        }
                        onSubmitReply(thread.id, value)
                        setReplyDrafts((previous) => ({
                          ...previous,
                          [thread.id]: '',
                        }))
                      }}
                      className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Reply
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
