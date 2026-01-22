import { useState } from 'react'
import {
  X,
  FileText,
  User,
  Building2,
  Clock,
  CheckCircle,
  Send,
  HelpCircle,
  Lightbulb,
  AlertTriangle,
  MoreHorizontal,
  ExternalLink,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import type { FeedbackDetailResponse, FeedbackStatus, FeedbackType } from '@/types'

interface FeedbackResponseDialogProps {
  feedback: FeedbackDetailResponse
  onClose: () => void
  onRespond: (response: string) => void
  onUpdateStatus: (status: FeedbackStatus) => void
  isLoading: boolean
}

const typeConfig: Record<FeedbackType, { label: string; icon: React.ReactNode; className: string }> = {
  question: {
    label: 'Question',
    icon: <HelpCircle className="w-4 h-4" />,
    className: 'text-blue-600 bg-blue-50',
  },
  suggestion: {
    label: 'Suggestion',
    icon: <Lightbulb className="w-4 h-4" />,
    className: 'text-purple-600 bg-purple-50',
  },
  issue: {
    label: 'Issue',
    icon: <AlertTriangle className="w-4 h-4" />,
    className: 'text-red-600 bg-red-50',
  },
  other: {
    label: 'Other',
    icon: <MoreHorizontal className="w-4 h-4" />,
    className: 'text-gray-600 bg-gray-50',
  },
}

export default function FeedbackResponseDialog({
  feedback,
  onClose,
  onRespond,
  onUpdateStatus,
  isLoading,
}: FeedbackResponseDialogProps) {
  const [response, setResponse] = useState(feedback.response || '')
  const type = typeConfig[feedback.feedback_type]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!response.trim()) return
    onRespond(response)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${type.className}`}>
              {type.icon}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {type.label} from {feedback.user_name}
              </h2>
              <p className="text-sm text-gray-500">
                {new Date(feedback.created_at).toLocaleString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Customer Info */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <User className="w-4 h-4" />
              <span>{feedback.user_name}</span>
            </div>
            {feedback.tenant_name && (
              <div className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                <span>{feedback.tenant_name}</span>
              </div>
            )}
          </div>

          {/* Document Link */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-2">Document</p>
            <Link
              to={`/documents/${feedback.document_id}`}
              target="_blank"
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700"
            >
              <FileText className="w-4 h-4" />
              <span className="font-medium">{feedback.document_title}</span>
              {feedback.document_number && (
                <span className="text-gray-500">#{feedback.document_number}</span>
              )}
              <ExternalLink className="w-3 h-3 ml-auto" />
            </Link>
          </div>

          {/* Original Feedback */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Feedback</p>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-800 whitespace-pre-wrap">{feedback.content}</p>
            </div>
          </div>

          {/* Existing Response */}
          {feedback.response && feedback.responded_at && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Response from {feedback.responder_name}
              </p>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-gray-800 whitespace-pre-wrap">{feedback.response}</p>
                <p className="text-xs text-gray-500 mt-2">
                  Responded on {new Date(feedback.responded_at).toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {/* Response Form */}
          {feedback.status === 'pending' && (
            <form onSubmit={handleSubmit}>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Response
              </label>
              <textarea
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                rows={5}
                placeholder="Type your response to the customer..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Status:</span>
            <span
              className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full ${
                feedback.status === 'pending'
                  ? 'bg-yellow-100 text-yellow-700'
                  : feedback.status === 'responded'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {feedback.status === 'pending' && <Clock className="w-3 h-3" />}
              {feedback.status === 'responded' && <CheckCircle className="w-3 h-3" />}
              {feedback.status.charAt(0).toUpperCase() + feedback.status.slice(1)}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:text-gray-900"
            >
              Close
            </button>

            {feedback.status === 'responded' && (
              <button
                onClick={() => onUpdateStatus('closed')}
                disabled={isLoading}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50"
              >
                Mark as Closed
              </button>
            )}

            {feedback.status === 'pending' && (
              <button
                onClick={handleSubmit}
                disabled={isLoading || !response.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                Send Response
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
