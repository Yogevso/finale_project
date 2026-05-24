/**
 * MyFeedbackPage - Customer's feedback history
 */
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { portalApi, type FeedbackItem } from '../../lib/portalApi'
import PageHeader from '@/components/PageHeader'
import { ListSkeleton } from '@/components/skeletons'
import {
  MessageSquare,
  Clock,
  CheckCircle,
  XCircle,
  ChevronRight,
  FileText,
  HelpCircle,
  Lightbulb,
  AlertTriangle,
  X,
} from 'lucide-react'

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const statusConfig = {
  pending: {
    label: 'Pending',
    icon: Clock,
    bgColor: 'bg-amber-100 dark:bg-amber-950/50',
    textColor: 'text-amber-700 dark:text-amber-200',
  },
  responded: {
    label: 'Responded',
    icon: CheckCircle,
    bgColor: 'bg-emerald-100 dark:bg-emerald-950/50',
    textColor: 'text-emerald-700 dark:text-emerald-200',
  },
  closed: {
    label: 'Closed',
    icon: XCircle,
    bgColor: 'bg-slate-100 dark:bg-slate-800',
    textColor: 'text-slate-700 dark:text-slate-200',
  },
}

const typeConfig = {
  question: { label: 'Question', icon: HelpCircle, color: 'text-blue-600 dark:text-blue-300' },
  suggestion: { label: 'Suggestion', icon: Lightbulb, color: 'text-amber-600 dark:text-amber-300' },
  issue: { label: 'Issue', icon: AlertTriangle, color: 'text-rose-600 dark:text-rose-300' },
  other: { label: 'Other', icon: MessageSquare, color: 'text-slate-600 dark:text-slate-300' },
}

export default function MyFeedbackPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [statusFilter, setStatusFilter] = useState<'pending' | 'responded' | 'closed' | ''>('')
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null)
  const selectedFeedbackId = Number(searchParams.get('feedback') || '')

  const openFeedbackDetails = (feedback: FeedbackItem) => {
    setSelectedFeedback(feedback)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('feedback', String(feedback.id))
    setSearchParams(nextParams, { replace: true })
  }

  const closeFeedbackDetails = () => {
    setSelectedFeedback(null)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('feedback')
    setSearchParams(nextParams, { replace: true })
  }

  const {
    data: feedback,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['portal', 'feedback', { status: statusFilter || undefined }],
    queryFn: () => portalApi.getFeedbackList({ status: statusFilter || undefined }),
  })

  const feedbackDetailQuery = useQuery({
    queryKey: ['portal', 'feedback-detail', selectedFeedbackId],
    queryFn: () => portalApi.getFeedback(selectedFeedbackId),
    enabled: Number.isInteger(selectedFeedbackId) && selectedFeedbackId > 0,
  })

  useEffect(() => {
    if (feedbackDetailQuery.data) {
      setSelectedFeedback(feedbackDetailQuery.data)
    }
  }, [feedbackDetailQuery.data])

  const buildDocumentLink = (item: FeedbackItem) =>
    item.anchor_text
      ? `/portal/documents/${item.document_id}?fullscreen=1&highlight=${encodeURIComponent(item.anchor_text)}`
      : `/portal/documents/${item.document_id}?fullscreen=1`

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Customer Portal"
        title="My Feedback"
        subtitle="Track feedback submissions and responses from the team."
      />

      <div className="surface-card rounded-2xl p-4">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setStatusFilter('')}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
              !statusFilter
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-200'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
            type="button"
          >
            All
          </button>
          {Object.entries(statusConfig).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key as typeof statusFilter)}
              className={`inline-flex items-center rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                statusFilter === key
                  ? `${config.bgColor} ${config.textColor}`
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
              type="button"
            >
              <config.icon className="mr-2 h-4 w-4" />
              {config.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : isError ? (
        <ErrorState
          title="Feedback could not be loaded"
          message="We could not fetch your feedback history."
          onRetry={() => void refetch()}
        />
      ) : feedback?.items.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-8 w-8" aria-hidden="true" />}
          title="No feedback yet"
          description={
            statusFilter
              ? `You don't have any ${statusFilter} feedback yet.`
              : "You haven't submitted any feedback yet."
          }
          action={{ label: 'Browse Documents', onClick: () => navigate('/portal/documents') }}
        />
      ) : (
        <div className="surface-card divide-y divide-slate-200 rounded-2xl dark:divide-slate-800">
          {feedback?.items.map((item) => {
            const status = statusConfig[item.status]
            const type = typeConfig[item.feedback_type]
            const TypeIcon = type.icon
            const StatusIcon = status.icon

            return (
              <div
                key={item.id}
                className="cursor-pointer p-4 hover:bg-slate-50 dark:hover:bg-slate-800/70"
                onClick={() => openFeedbackDetails(item)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    openFeedbackDetails(item)
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <div className="flex items-start justify-between">
                  <div className="flex min-w-0 items-start">
                    <TypeIcon className={`mt-0.5 h-6 w-6 flex-shrink-0 ${type.color}`} />
                    <div className="ml-3 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="body-copy">{type.label}</span>
                        <span className="helper-copy">-</span>
                        <Link
                          to={buildDocumentLink(item)}
                          className="card-title truncate text-blue-600 hover:text-blue-500"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {item.document_title}
                        </Link>
                      </div>
                      {item.anchor_text ? (
                        <p className="helper-copy mt-1 italic">
                          On selected text: "{item.anchor_text}"
                        </p>
                      ) : null}
                      <p className="body-copy mt-1 line-clamp-2 text-slate-900 dark:text-slate-100">{item.content}</p>
                      <p className="helper-copy mt-2">
                        Submitted {formatDate(item.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <span className={`pill ${status.bgColor} ${status.textColor}`}>
                      <StatusIcon className="mr-1 h-3.5 w-3.5" />
                      {status.label}
                    </span>
                    <ChevronRight className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {selectedFeedback && (
        <div className="modal-overlay flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0"
            onClick={() => setSelectedFeedback(null)}
            aria-label="Close feedback details"
          />
          <div className="modal-content relative max-h-[90vh] w-full max-w-2xl overflow-y-auto">
            <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <h2 className="section-title">
                  Feedback Details
                </h2>
                <button
                  onClick={closeFeedbackDetails}
                  className="btn-icon h-9 w-9"
                  type="button"
                  aria-label="Close feedback details"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="space-y-6 p-6">
              <div className="flex items-center gap-4">
                <span
                  className={`pill ${
                    statusConfig[selectedFeedback.status].bgColor
                  } ${statusConfig[selectedFeedback.status].textColor}`}
                >
                  {statusConfig[selectedFeedback.status].label}
                </span>
                <span className="body-copy">
                  {typeConfig[selectedFeedback.feedback_type].label}
                </span>
              </div>

              <div>
                <p className="helper-copy">Document</p>
                <Link
                  to={buildDocumentLink(selectedFeedback)}
                  className="card-title mt-1 flex items-center text-blue-600 hover:text-blue-500"
                  onClick={() => setSelectedFeedback(null)}
                >
                  <FileText className="mr-2 h-5 w-5" />
                  {selectedFeedback.document_title}
                </Link>
              </div>

              {selectedFeedback.anchor_text ? (
                <div>
                  <p className="helper-copy">Selected Text</p>
                  <div className="mt-1 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/40">
                    <p className="body-copy whitespace-pre-wrap italic text-slate-900 dark:text-slate-100">
                      "{selectedFeedback.anchor_text}"
                    </p>
                  </div>
                </div>
              ) : null}

              <div>
                <p className="helper-copy">Your Feedback</p>
                <div className="mt-1 rounded-xl bg-slate-50 p-4 dark:bg-slate-950">
                  <p className="body-copy whitespace-pre-wrap text-slate-900 dark:text-slate-100">
                    {selectedFeedback.content}
                  </p>
                </div>
                <p className="helper-copy mt-2">
                  Submitted {formatDate(selectedFeedback.created_at)}
                </p>
              </div>

              {selectedFeedback.response && (
                <div>
                  <p className="helper-copy">Response</p>
                  <div className="mt-1 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950/40">
                    <p className="body-copy whitespace-pre-wrap text-slate-900 dark:text-slate-100">
                      {selectedFeedback.response}
                    </p>
                  </div>
                  <p className="helper-copy mt-2">
                    {selectedFeedback.responded_by_name && (
                      <span>By {selectedFeedback.responded_by_name} - </span>
                    )}
                    {selectedFeedback.responded_at && formatDate(selectedFeedback.responded_at)}
                  </p>
                </div>
              )}

              {selectedFeedback.ticket_id ? (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/40">
                  <p className="body-copy text-slate-900 dark:text-slate-100">
                    This feedback was escalated into a support conversation.
                  </p>
                  <Link
                    to={`/portal/support?ticket=${selectedFeedback.ticket_id}`}
                    className="btn-primary table-action-btn mt-3 inline-flex"
                    onClick={closeFeedbackDetails}
                  >
                    Open support conversation
                  </Link>
                </div>
              ) : null}

              {selectedFeedback.status === 'pending' && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/40">
                  <div className="flex items-center">
                    <Clock className="mr-2 h-5 w-5 text-amber-600 dark:text-amber-300" />
                    <p className="text-amber-700 dark:text-amber-200">
                      Your feedback is being reviewed. We'll respond soon!
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-b-2xl border-t border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-950">
              <button
                onClick={closeFeedbackDetails}
                className="btn-secondary table-action-btn w-full"
                type="button"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
