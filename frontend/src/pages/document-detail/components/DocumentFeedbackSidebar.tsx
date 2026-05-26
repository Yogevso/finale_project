import type { FeedbackDetailResponse } from '@/types'
import { MessageSquareText } from 'lucide-react'

interface DocumentFeedbackSidebarProps {
  feedbackItems: FeedbackDetailResponse[]
  isLoading: boolean
  isError: boolean
}

function formatTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function statusLabel(status: FeedbackDetailResponse['status']): string {
  if (status === 'pending') return 'Pending'
  if (status === 'responded') return 'Responded'
  return 'Closed'
}

function statusClasses(status: FeedbackDetailResponse['status']): string {
  if (status === 'pending') {
    return 'border border-amber-200 bg-amber-50 text-amber-700'
  }
  if (status === 'responded') {
    return 'border border-blue-200 bg-blue-50 text-blue-700'
  }
  return 'border border-slate-200 bg-slate-50 text-slate-600'
}

export function DocumentFeedbackSidebar({
  feedbackItems,
  isLoading,
  isError,
}: DocumentFeedbackSidebarProps) {
  return (
    <aside className="document-comments-sidebar flex w-full flex-col border-t border-slate-200 bg-white md:w-[21rem] md:min-w-[19rem] md:max-w-[24rem] md:border-l md:border-t-0">
      <div className="border-b border-slate-200 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Feedback</p>
        <p className="mt-1 text-sm text-slate-600">{feedbackItems.length} item{feedbackItems.length === 1 ? '' : 's'}</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {isLoading ? <p className="text-sm text-slate-500">Loading feedback...</p> : null}
        {isError ? (
          <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            Failed to load feedback.
          </p>
        ) : null}
        {!isLoading && !isError && feedbackItems.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-center">
            <MessageSquareText className="mx-auto h-5 w-5 text-slate-400" />
            <p className="mt-2 text-sm font-medium text-slate-700">No feedback for this document</p>
            <p className="mt-1 text-xs text-slate-500">Feedback entries will appear here.</p>
          </div>
        ) : null}

        <div className="space-y-3">
          {feedbackItems.map((item) => (
            <article key={item.id} className="rounded-2xl border border-slate-200 bg-white px-3 py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-slate-800">{item.user_name}</p>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClasses(item.status)}`}>
                  {statusLabel(item.status)}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">{formatTimestamp(item.created_at)}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{item.content}</p>
              {item.response ? (
                <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Response</p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-blue-900">{item.response}</p>
                  {item.responded_at ? (
                    <p className="mt-1 text-[11px] text-blue-700">{formatTimestamp(item.responded_at)}</p>
                  ) : null}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </aside>
  )
}
