import { useState, useEffect, useId, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  X, 
  FileText, 
  User, 
  Calendar, 
  MessageSquare,
  CheckCircle,
  XCircle,
  AlertTriangle,
  GitBranch
} from 'lucide-react'
import type { ReviewRequest, Version } from '@/types'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface ReviewDialogProps {
  review: ReviewRequest
  onClose: () => void
  onApprove: (comments?: string) => void
  onReject: (comments: string) => void
  isLoading: boolean
}

export default function ReviewDialog({
  review,
  onClose,
  onApprove,
  onReject,
  isLoading,
}: ReviewDialogProps) {
  const [comments, setComments] = useState('')
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const [version, setVersion] = useState<Version | null>(null)
  const [loadingVersion, setLoadingVersion] = useState(false)
  const titleId = useId()
  const commentsErrorId = useId()
  const commentsRef = useRef<HTMLTextAreaElement>(null)

  const { containerRef } = useFocusTrap(onClose)
  const showRejectionError = action === 'reject' && showConfirm && !comments.trim()

  // Fetch version details if version_id is present
  useEffect(() => {
    if (review.version_id && review.document_id) {
      setLoadingVersion(true)
      api.getVersion(review.document_id, review.version_id)
        .then(setVersion)
        .catch(console.error)
        .finally(() => setLoadingVersion(false))
    }
  }, [review.version_id, review.document_id])

  const handleAction = (selectedAction: 'approve' | 'reject') => {
    setAction(selectedAction)
    setShowConfirm(true)
  }

  const handleConfirm = () => {
    if (action === 'approve') {
      onApprove(comments || undefined)
    } else if (action === 'reject') {
      if (!comments.trim()) {
        commentsRef.current?.focus()
        return
      }
      onReject(comments)
    }
  }

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close review dialog"
        tabIndex={-1}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="modal-content motion-enter-scale relative z-10 max-h-[90vh] w-full max-w-2xl overflow-hidden dark:bg-slate-900"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h2 id={titleId} className="text-lg font-semibold text-slate-900 font-display dark:text-slate-100">Review Document</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Close review dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* Document Info */}
          <div className="surface-muted p-4 space-y-3">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-sky-600" />
              <div>
                <Link
                  to={`/documents/${review.document_id}/fullscreen`}
                  target="_blank"
                  className="text-lg font-medium text-sky-700 hover:text-sky-800"
                >
                  {review.document?.title || `Document #${review.document_id}`}
                </Link>
                <p className="text-sm text-slate-500">
                  {review.document?.document_number}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2 text-slate-600">
                <User className="w-4 h-4" />
                <span>Submitted by: {review.submitter?.full_name || 'Unknown'}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Calendar className="w-4 h-4" />
                <span>Date: {formatDate(review.submitted_at)}</span>
              </div>
            </div>

            {review.message && (
              <div className="pt-2 border-t border-slate-200">
                <div className="flex items-start gap-2 text-slate-600">
                  <MessageSquare className="w-4 h-4 mt-0.5" />
                  <div>
                    <span className="text-xs font-medium text-slate-500">Submission Message:</span>
                    <p className="mt-1">{review.message}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Changes Summary */}
          {review.version_id && (
            <div className="bg-amber-50 rounded-2xl p-4 border border-amber-200">
              <div className="flex items-start gap-2">
                <GitBranch className="w-4 h-4 mt-0.5 text-amber-600" />
                <div className="flex-1">
                  <span className="text-xs font-medium text-amber-700">Changes Made:</span>
                  {loadingVersion ? (
                    <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-slate-300 border-t-amber-600"></div>
                      Loading changes…
                    </div>
                  ) : version?.changes_summary ? (
                    <>
                      <div className="mt-2 text-xs text-slate-600">
                        <span className="font-medium text-slate-700">
                          Version:
                        </span>{' '}
                        v{version.semantic_version || `${version.version_number}.0.0`}
                      </div>
                      {version.created_by_user && (
                        <div className="text-xs text-slate-600">
                          <span className="font-medium text-slate-700">Editor:</span>{' '}
                          {version.created_by_user.full_name} ({version.created_by_user.role.replace('_', ' ')})
                        </div>
                      )}
                      <pre className="mt-2 text-sm text-slate-700 whitespace-pre-wrap font-mono bg-white p-3 rounded-xl border border-amber-100">
                        {version.changes_summary}
                      </pre>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-slate-500 italic">No detailed changes recorded</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* View Document Link */}
          <div className="text-center">
            <Link
              to={`/documents/${review.document_id}/fullscreen`}
              target="_blank"
              className="text-sky-600 hover:text-sky-700 text-sm underline"
            >
              Open document in new tab to review content →
            </Link>
          </div>

          {/* Comments */}
          <div>
            <label htmlFor="review-comments" className="block text-sm font-medium text-slate-700 mb-2">
              Review Comments {action === 'reject' && <span className="text-rose-500">*</span>}
            </label>
            <textarea
              ref={commentsRef}
              id="review-comments"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder={
                action === 'reject'
                  ? 'Please explain why this document is being rejected...'
                  : 'Optional comments for the submitter...'
              }
              rows={4}
              className="input-field"
              disabled={isLoading}
              required={action === 'reject'}
              aria-required={action === 'reject'}
              aria-invalid={showRejectionError}
              aria-describedby={showRejectionError ? commentsErrorId : undefined}
            />
            {showRejectionError ? (
              <p id={commentsErrorId} role="alert" className="mt-2 text-sm text-rose-600">
                Rejection comments are required before you can confirm.
              </p>
            ) : null}
          </div>

          {/* Confirmation */}
          {showConfirm && (
            <div
              className={`p-4 rounded-2xl border ${
                action === 'approve'
                  ? 'bg-emerald-50 border-emerald-200'
                  : 'bg-rose-50 border-rose-200'
              }`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle
                  className={`w-5 h-5 ${
                    action === 'approve' ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                />
                <div>
                  <p
                    className={`font-medium ${
                      action === 'approve' ? 'text-emerald-800' : 'text-rose-800'
                    }`}
                  >
                    {action === 'approve'
                      ? 'Confirm Approval'
                      : 'Confirm Rejection'}
                  </p>
                  <p
                    className={`text-sm mt-1 ${
                      action === 'approve' ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {action === 'approve'
                      ? 'This will mark the document as approved (not published yet) and notify the submitter.'
                      : 'This will return the document to draft status and notify the submitter.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-950/70">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="btn-ghost"
          >
            Cancel
          </button>

          <div className="flex items-center gap-3">
            {!showConfirm ? (
              <>
                <button
                  type="button"
                  onClick={() => handleAction('reject')}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-rose-100 text-rose-700 rounded-full hover:bg-rose-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
                <button
                  type="button"
                  onClick={() => handleAction('approve')}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-full hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
                >
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setShowConfirm(false)}
                  disabled={isLoading}
                  className="btn-ghost"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  disabled={isLoading || (action === 'reject' && !comments.trim())}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full disabled:opacity-50 disabled:cursor-not-allowed font-medium transition ${
                    action === 'approve'
                      ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                      : 'bg-rose-600 text-white hover:bg-rose-700'
                  }`}
                >
                  {isLoading ? (
                    'Processing...'
                  ) : action === 'approve' ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Confirm Approval
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" />
                      Confirm Rejection
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
