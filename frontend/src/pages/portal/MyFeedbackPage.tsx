/**
 * MyFeedbackPage - Customer's feedback history
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { portalApi, FeedbackItem } from '../../lib/portalApi'
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
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-700',
  },
  responded: {
    label: 'Responded',
    icon: CheckCircle,
    bgColor: 'bg-emerald-100',
    textColor: 'text-emerald-700',
  },
  closed: {
    label: 'Closed',
    icon: XCircle,
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-700',
  },
}

const typeConfig = {
  question: { label: 'Question', icon: HelpCircle, color: 'text-sky-600' },
  suggestion: { label: 'Suggestion', icon: Lightbulb, color: 'text-amber-600' },
  issue: { label: 'Issue', icon: AlertTriangle, color: 'text-rose-600' },
  other: { label: 'Other', icon: MessageSquare, color: 'text-slate-600' },
}

export default function MyFeedbackPage() {
  const [statusFilter, setStatusFilter] = useState<'pending' | 'responded' | 'closed' | ''>('')
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null)

  // Fetch feedback
  const { data: feedback, isLoading } = useQuery({
    queryKey: ['portal', 'feedback', { status: statusFilter || undefined }],
    queryFn: () => portalApi.getFeedbackList({ status: statusFilter || undefined }),
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-slate-900">My Feedback</h1>
        <p className="mt-1 text-slate-500">Track your feedback submissions and responses</p>
      </div>

      {/* Status filter */}
      <div className="surface-card rounded-2xl p-4">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setStatusFilter('')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              !statusFilter
                ? 'bg-sky-100 text-sky-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            All
          </button>
          {Object.entries(statusConfig).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key as typeof statusFilter)}
              className={`inline-flex items-center px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                statusFilter === key
                  ? `${config.bgColor} ${config.textColor}`
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <config.icon className="h-4 w-4 mr-2" />
              {config.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feedback list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sky-600"></div>
        </div>
      ) : feedback?.items.length === 0 ? (
        <div className="text-center py-12 surface-card rounded-2xl">
          <MessageSquare className="h-16 w-16 mx-auto text-slate-300" />
          <h3 className="mt-4 text-lg font-display font-medium text-slate-900">No feedback yet</h3>
          <p className="mt-2 text-slate-500">
            {statusFilter
              ? `You don't have any ${statusFilter} feedback`
              : "You haven't submitted any feedback yet"}
          </p>
          <Link
            to="/portal/documents"
            className="mt-4 inline-flex items-center text-sky-600 hover:text-sky-500"
          >
            Browse documents to get started
          </Link>
        </div>
      ) : (
        <div className="surface-card rounded-2xl divide-y divide-slate-200">
          {feedback?.items.map((item) => {
            const status = statusConfig[item.status]
            const type = typeConfig[item.feedback_type]
            const TypeIcon = type.icon
            const StatusIcon = status.icon

            return (
              <div
                key={item.id}
                className="p-4 hover:bg-slate-50 cursor-pointer"
                onClick={() => setSelectedFeedback(item)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start min-w-0">
                    <TypeIcon className={`h-6 w-6 ${type.color} flex-shrink-0 mt-0.5`} />
                    <div className="ml-3 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-500">{type.label}</span>
                        <span className="text-slate-300">•</span>
                        <Link
                          to={`/portal/documents/${item.document_id}?fullscreen=1`}
                          className="text-sm text-sky-600 hover:text-sky-500 truncate"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {item.document_title}
                        </Link>
                      </div>
                      <p className="mt-1 text-slate-900 line-clamp-2">{item.content}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        Submitted {formatDate(item.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <span
                      className={`pill ${status.bgColor} ${status.textColor}`}
                    >
                      <StatusIcon className="h-3.5 w-3.5 mr-1" />
                      {status.label}
                    </span>
                    <ChevronRight className="h-5 w-5 text-slate-400" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Feedback detail modal */}
      {selectedFeedback && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            <div
              className="fixed inset-0 bg-slate-900 bg-opacity-75"
              onClick={() => setSelectedFeedback(null)}
            />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              {/* Modal header */}
              <div className="px-6 py-4 border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-display font-semibold text-slate-900">Feedback Details</h2>
                  <button
                    onClick={() => setSelectedFeedback(null)}
                    className="text-slate-400 hover:text-slate-500"
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* Modal content */}
              <div className="p-6 space-y-6">
                {/* Status and type */}
                <div className="flex items-center gap-4">
                  <span
                    className={`pill ${
                      statusConfig[selectedFeedback.status].bgColor
                    } ${statusConfig[selectedFeedback.status].textColor}`}
                  >
                    {statusConfig[selectedFeedback.status].label}
                  </span>
                  <span className="text-sm text-slate-500">
                    {typeConfig[selectedFeedback.feedback_type].label}
                  </span>
                </div>

                {/* Document link */}
                <div>
                  <label className="text-sm font-medium text-slate-500">Document</label>
                  <Link
                    to={`/portal/documents/${selectedFeedback.document_id}?fullscreen=1`}
                    className="mt-1 flex items-center text-sky-600 hover:text-sky-500"
                    onClick={() => setSelectedFeedback(null)}
                  >
                    <FileText className="h-5 w-5 mr-2" />
                    {selectedFeedback.document_title}
                  </Link>
                </div>

                {/* Your feedback */}
                <div>
                  <label className="text-sm font-medium text-slate-500">Your Feedback</label>
                  <div className="mt-1 p-4 bg-slate-50 rounded-xl">
                    <p className="text-slate-900 whitespace-pre-wrap">{selectedFeedback.content}</p>
                  </div>
                  <p className="mt-2 text-xs text-slate-400">
                    Submitted {formatDate(selectedFeedback.created_at)}
                  </p>
                </div>

                {/* Response */}
                {selectedFeedback.response && (
                  <div>
                    <label className="text-sm font-medium text-slate-500">Response</label>
                    <div className="mt-1 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                      <p className="text-slate-900 whitespace-pre-wrap">
                        {selectedFeedback.response}
                      </p>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      {selectedFeedback.responded_by_name && (
                        <span>By {selectedFeedback.responded_by_name} • </span>
                      )}
                      {selectedFeedback.responded_at && formatDate(selectedFeedback.responded_at)}
                    </p>
                  </div>
                )}

                {/* Pending message */}
                {selectedFeedback.status === 'pending' && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                    <div className="flex items-center">
                      <Clock className="h-5 w-5 text-amber-600 mr-2" />
                      <p className="text-amber-700">
                        Your feedback is being reviewed. We'll respond soon!
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal footer */}
              <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
                <button
                  onClick={() => setSelectedFeedback(null)}
                  className="w-full px-4 py-2 bg-slate-200 text-slate-700 rounded-xl hover:bg-slate-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
