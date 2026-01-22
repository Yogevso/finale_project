import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  X, 
  FileText, 
  User, 
  Calendar, 
  MessageSquare,
  CheckCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react'
import type { ReviewRequest } from '@/types'

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

  const handleAction = (selectedAction: 'approve' | 'reject') => {
    setAction(selectedAction)
    setShowConfirm(true)
  }

  const handleConfirm = () => {
    if (action === 'approve') {
      onApprove(comments || undefined)
    } else if (action === 'reject') {
      if (!comments.trim()) {
        alert('Please provide a reason for rejection')
        return
      }
      onReject(comments)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Review Document</h2>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* Document Info */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-blue-600" />
              <div>
                <Link
                  to={`/documents/${review.document_id}`}
                  target="_blank"
                  className="text-lg font-medium text-blue-600 hover:text-blue-700"
                >
                  {review.document?.title || `Document #${review.document_id}`}
                </Link>
                <p className="text-sm text-gray-500">
                  {review.document?.document_number}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2 text-gray-600">
                <User className="w-4 h-4" />
                <span>Submitted by: {review.submitter?.full_name || 'Unknown'}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Calendar className="w-4 h-4" />
                <span>Date: {new Date(review.submitted_at).toLocaleString()}</span>
              </div>
            </div>

            {review.message && (
              <div className="pt-2 border-t border-gray-200">
                <div className="flex items-start gap-2 text-gray-600">
                  <MessageSquare className="w-4 h-4 mt-0.5" />
                  <div>
                    <span className="text-xs font-medium text-gray-500">Submission Message:</span>
                    <p className="mt-1">{review.message}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* View Document Link */}
          <div className="text-center">
            <Link
              to={`/documents/${review.document_id}`}
              target="_blank"
              className="text-blue-600 hover:text-blue-700 text-sm underline"
            >
              Open document in new tab to review content →
            </Link>
          </div>

          {/* Comments */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Review Comments {action === 'reject' && <span className="text-red-500">*</span>}
            </label>
            <textarea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder={
                action === 'reject'
                  ? 'Please explain why this document is being rejected...'
                  : 'Optional comments for the submitter...'
              }
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
          </div>

          {/* Confirmation */}
          {showConfirm && (
            <div
              className={`p-4 rounded-lg border ${
                action === 'approve'
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle
                  className={`w-5 h-5 ${
                    action === 'approve' ? 'text-green-600' : 'text-red-600'
                  }`}
                />
                <div>
                  <p
                    className={`font-medium ${
                      action === 'approve' ? 'text-green-800' : 'text-red-800'
                    }`}
                  >
                    {action === 'approve'
                      ? 'Confirm Approval'
                      : 'Confirm Rejection'}
                  </p>
                  <p
                    className={`text-sm mt-1 ${
                      action === 'approve' ? 'text-green-700' : 'text-red-700'
                    }`}
                  >
                    {action === 'approve'
                      ? 'This will publish the document and notify the submitter.'
                      : 'This will return the document to draft status and notify the submitter.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            Cancel
          </button>

          <div className="flex items-center gap-3">
            {!showConfirm ? (
              <>
                <button
                  onClick={() => handleAction('reject')}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
                <button
                  onClick={() => handleAction('approve')}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setShowConfirm(false)}
                  disabled={isLoading}
                  className="px-4 py-2 text-gray-700 hover:text-gray-900"
                >
                  Back
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={isLoading || (action === 'reject' && !comments.trim())}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg disabled:opacity-50 ${
                    action === 'approve'
                      ? 'bg-green-600 text-white hover:bg-green-700'
                      : 'bg-red-600 text-white hover:bg-red-700'
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
