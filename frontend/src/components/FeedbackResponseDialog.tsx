import { useId, useState } from 'react'
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
import { formatDate } from '@/lib/dateUtils'
import {
  COMMUNICATION_INPUT_LIMITS,
  normalizeMultilineInput,
} from '@/lib/uiInputRules'
import type { FeedbackDetailResponse, FeedbackStatus, FeedbackType } from '@/types'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface FeedbackResponseDialogProps {
  feedback: FeedbackDetailResponse
  onClose: () => void
  onRespond: (response: string) => void
  onUpdateStatus: (status: FeedbackStatus) => void
  onEscalate?: () => void
  isLoading: boolean
}

const typeConfig: Record<FeedbackType, { label: string; icon: React.ReactNode; className: string }> = {
  question: {
    label: 'Question',
    icon: <HelpCircle className="w-4 h-4" />,
    className: 'text-sky-600 bg-sky-50',
  },
  suggestion: {
    label: 'Suggestion',
    icon: <Lightbulb className="w-4 h-4" />,
    className: 'text-purple-600 bg-purple-50',
  },
  issue: {
    label: 'Issue',
    icon: <AlertTriangle className="w-4 h-4" />,
    className: 'text-rose-600 bg-rose-50',
  },
  other: {
    label: 'Other',
    icon: <MoreHorizontal className="w-4 h-4" />,
    className: 'text-slate-600 bg-slate-50',
  },
}

export default function FeedbackResponseDialog({
  feedback,
  onClose,
  onRespond,
  onUpdateStatus,
  onEscalate,
  isLoading,
}: FeedbackResponseDialogProps) {
  const [response, setResponse] = useState(feedback.response || '')
  const [responseError, setResponseError] = useState('')
  const titleId = useId()
  const type = typeConfig[feedback.feedback_type]

  const { containerRef } = useFocusTrap(onClose)

  const submitResponse = () => {
    const normalizedResponse = normalizeMultilineInput(
      response,
      COMMUNICATION_INPUT_LIMITS.feedbackResponse,
    )
    if (!normalizedResponse) {
      setResponseError('A response is required before sending.')
      return
    }

    setResponseError('')
    onRespond(normalizedResponse)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    submitResponse()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/50"
        onClick={onClose}
        aria-label="Close feedback dialog"
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative z-10 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl ${type.className}`}>
              {type.icon}
            </div>
            <div>
              <h2 id={titleId} className="text-lg font-display font-semibold text-slate-900">
                {type.label} from {feedback.user_name}
              </h2>
              <p className="text-sm text-slate-500">
                {formatDate(feedback.created_at)}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600"
            aria-label="Close feedback dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Customer Info */}
          <div className="flex items-center gap-4 text-sm text-slate-600">
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
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-sm text-slate-500 mb-2">Document</p>
            <Link
              to={`/documents/${feedback.document_id}/fullscreen`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 text-sky-600 hover:text-sky-700"
            >
              <FileText className="w-4 h-4" />
              <span className="font-medium">{feedback.document_title}</span>
              {feedback.document_number && (
                <span className="text-slate-500">#{feedback.document_number}</span>
              )}
              <ExternalLink className="w-3 h-3 ml-auto" />
            </Link>
          </div>

          {/* Original Feedback */}
          <div>
            <p className="text-sm font-medium text-slate-700 mb-2">Feedback</p>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-slate-800 whitespace-pre-wrap">{feedback.content}</p>
            </div>
          </div>

          {/* Existing Response */}
          {feedback.response && feedback.responded_at && (
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-500" />
                Response from {feedback.responder_name}
              </p>
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <p className="text-slate-800 whitespace-pre-wrap">{feedback.response}</p>
                <p className="text-xs text-slate-500 mt-2">
                  Responded on {formatDate(feedback.responded_at)}
                </p>
              </div>
            </div>
          )}

          {/* Response Form */}
          {feedback.status === 'pending' && (
            <form onSubmit={handleSubmit}>
              <label htmlFor="feedback-response" className="block text-sm font-medium text-slate-700 mb-2">
                Your Response <span className="text-rose-500">*</span>
              </label>
              <textarea
                id="feedback-response"
                value={response}
                onChange={(e) => {
                  setResponse(e.target.value)
                  if (responseError) {
                    setResponseError('')
                  }
                }}
                rows={5}
                placeholder="Type your response to the customer..."
                className="input-field resize-none"
                maxLength={COMMUNICATION_INPUT_LIMITS.feedbackResponse}
                required
                aria-invalid={!!responseError}
                aria-describedby={responseError ? 'feedback-response-error' : undefined}
              />
              <p className="mt-2 text-right text-xs text-slate-500">
                {response.length}/{COMMUNICATION_INPUT_LIMITS.feedbackResponse}
              </p>
              {responseError ? (
                <p id="feedback-response-error" role="alert" className="mt-2 text-sm text-rose-500">
                  {responseError}
                </p>
              ) : null}
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Status:</span>
            <span
              className={`pill flex items-center gap-1 ${
                feedback.status === 'pending'
                  ? 'bg-amber-100 text-amber-700'
                  : feedback.status === 'responded'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {feedback.status === 'pending' && <Clock className="w-3 h-3" />}
              {feedback.status === 'responded' && <CheckCircle className="w-3 h-3" />}
              {feedback.status.charAt(0).toUpperCase() + feedback.status.slice(1)}
            </span>
          </div>

        <div className="flex items-center gap-3">
          {!feedback.ticket_id && onEscalate ? (
            <button
              type="button"
              onClick={onEscalate}
              disabled={isLoading}
              className="btn-secondary disabled:opacity-50"
            >
              Escalate to Support
            </button>
          ) : null}
          {feedback.ticket_id ? (
            <Link
              to={`/support?ticket=${feedback.ticket_id}`}
              className="btn-secondary"
            >
              Open Support Conversation
            </Link>
          ) : null}
          <button
            type="button"
            onClick={onClose}
              className="btn-ghost"
            >
              Close
            </button>

            {feedback.status === 'responded' && (
              <button
                type="button"
                onClick={() => onUpdateStatus('closed')}
                disabled={isLoading}
                className="btn-secondary disabled:opacity-50"
              >
                Mark as Closed
              </button>
            )}

            {feedback.status === 'pending' && (
              <button
                type="button"
                onClick={submitResponse}
                disabled={isLoading || !response.trim()}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
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
