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
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-700',
  },
  responded: {
    label: 'Responded',
    icon: CheckCircle,
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
  },
  closed: {
    label: 'Closed',
    icon: XCircle,
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
  },
}

const typeConfig = {
  question: { label: 'Question', icon: HelpCircle, color: 'text-blue-600' },
  suggestion: { label: 'Suggestion', icon: Lightbulb, color: 'text-yellow-600' },
  issue: { label: 'Issue', icon: AlertTriangle, color: 'text-red-600' },
  other: { label: 'Other', icon: MessageSquare, color: 'text-gray-600' },
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
        <h1 className="text-2xl font-bold text-gray-900">My Feedback</h1>
        <p className="mt-1 text-gray-500">Track your feedback submissions and responses</p>
      </div>

      {/* Status filter */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setStatusFilter('')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              !statusFilter
                ? 'bg-indigo-100 text-indigo-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            All
          </button>
          {Object.entries(statusConfig).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key as typeof statusFilter)}
              className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === key
                  ? `${config.bgColor} ${config.textColor}`
                  : 'text-gray-600 hover:bg-gray-100'
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
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
        </div>
      ) : feedback?.items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <MessageSquare className="h-16 w-16 mx-auto text-gray-300" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No feedback yet</h3>
          <p className="mt-2 text-gray-500">
            {statusFilter
              ? `You don't have any ${statusFilter} feedback`
              : "You haven't submitted any feedback yet"}
          </p>
          <Link
            to="/portal/documents"
            className="mt-4 inline-flex items-center text-indigo-600 hover:text-indigo-500"
          >
            Browse documents to get started
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow divide-y">
          {feedback?.items.map((item) => {
            const status = statusConfig[item.status]
            const type = typeConfig[item.feedback_type]
            const TypeIcon = type.icon
            const StatusIcon = status.icon

            return (
              <div
                key={item.id}
                className="p-4 hover:bg-gray-50 cursor-pointer"
                onClick={() => setSelectedFeedback(item)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start min-w-0">
                    <TypeIcon className={`h-6 w-6 ${type.color} flex-shrink-0 mt-0.5`} />
                    <div className="ml-3 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">{type.label}</span>
                        <span className="text-gray-300">•</span>
                        <Link
                          to={`/portal/documents/${item.document_id}`}
                          className="text-sm text-indigo-600 hover:text-indigo-500 truncate"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {item.document_title}
                        </Link>
                      </div>
                      <p className="mt-1 text-gray-900 line-clamp-2">{item.content}</p>
                      <p className="mt-2 text-xs text-gray-400">
                        Submitted {formatDate(item.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${status.bgColor} ${status.textColor}`}
                    >
                      <StatusIcon className="h-3.5 w-3.5 mr-1" />
                      {status.label}
                    </span>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
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
              className="fixed inset-0 bg-gray-500 bg-opacity-75"
              onClick={() => setSelectedFeedback(null)}
            />
            <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              {/* Modal header */}
              <div className="px-6 py-4 border-b">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">Feedback Details</h2>
                  <button
                    onClick={() => setSelectedFeedback(null)}
                    className="text-gray-400 hover:text-gray-500"
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
                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                      statusConfig[selectedFeedback.status].bgColor
                    } ${statusConfig[selectedFeedback.status].textColor}`}
                  >
                    {statusConfig[selectedFeedback.status].label}
                  </span>
                  <span className="text-sm text-gray-500">
                    {typeConfig[selectedFeedback.feedback_type].label}
                  </span>
                </div>

                {/* Document link */}
                <div>
                  <label className="text-sm font-medium text-gray-500">Document</label>
                  <Link
                    to={`/portal/documents/${selectedFeedback.document_id}`}
                    className="mt-1 flex items-center text-indigo-600 hover:text-indigo-500"
                    onClick={() => setSelectedFeedback(null)}
                  >
                    <FileText className="h-5 w-5 mr-2" />
                    {selectedFeedback.document_title}
                  </Link>
                </div>

                {/* Your feedback */}
                <div>
                  <label className="text-sm font-medium text-gray-500">Your Feedback</label>
                  <div className="mt-1 p-4 bg-gray-50 rounded-lg">
                    <p className="text-gray-900 whitespace-pre-wrap">{selectedFeedback.content}</p>
                  </div>
                  <p className="mt-2 text-xs text-gray-400">
                    Submitted {formatDate(selectedFeedback.created_at)}
                  </p>
                </div>

                {/* Response */}
                {selectedFeedback.response && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Response</label>
                    <div className="mt-1 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <p className="text-gray-900 whitespace-pre-wrap">
                        {selectedFeedback.response}
                      </p>
                    </div>
                    <p className="mt-2 text-xs text-gray-400">
                      {selectedFeedback.responded_by_name && (
                        <span>By {selectedFeedback.responded_by_name} • </span>
                      )}
                      {selectedFeedback.responded_at && formatDate(selectedFeedback.responded_at)}
                    </p>
                  </div>
                )}

                {/* Pending message */}
                {selectedFeedback.status === 'pending' && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center">
                      <Clock className="h-5 w-5 text-yellow-600 mr-2" />
                      <p className="text-yellow-700">
                        Your feedback is being reviewed. We'll respond soon!
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal footer */}
              <div className="px-6 py-4 border-t bg-gray-50">
                <button
                  onClick={() => setSelectedFeedback(null)}
                  className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
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
