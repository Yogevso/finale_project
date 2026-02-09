import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Link } from 'react-router-dom'
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  FileText, 
  User, 
  Calendar,
  MessageSquare,
  AlertCircle,
  Send
} from 'lucide-react'
import type { ReviewRequest, ReviewStatus } from '@/types'
import ReviewDialog from '@/components/ReviewDialog'

type TabType = 'pending' | 'my-submissions'

const statusConfig: Record<ReviewStatus, { label: string; icon: React.ReactNode; className: string }> = {
  pending: {
    label: 'Pending',
    icon: <Clock className="w-4 h-4" />,
    className: 'bg-amber-100 text-amber-700',
  },
  approved: {
    label: 'Approved',
    icon: <CheckCircle className="w-4 h-4" />,
    className: 'bg-emerald-100 text-emerald-700',
  },
  rejected: {
    label: 'Rejected',
    icon: <XCircle className="w-4 h-4" />,
    className: 'bg-rose-100 text-rose-700',
  },
  cancelled: {
    label: 'Cancelled',
    icon: <AlertCircle className="w-4 h-4" />,
    className: 'bg-slate-100 text-slate-700',
  },
}

export default function ReviewsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('pending')
  const [selectedReview, setSelectedReview] = useState<ReviewRequest | null>(null)
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | ''>('')
  const queryClient = useQueryClient()

  // Fetch pending reviews
  const { data: pendingData, isLoading: pendingLoading } = useQuery({
    queryKey: ['reviews', 'pending'],
    queryFn: () => api.getPendingReviews({ per_page: 50 }),
    enabled: activeTab === 'pending',
  })

  // Fetch my submissions
  const { data: submissionsData, isLoading: submissionsLoading } = useQuery({
    queryKey: ['reviews', 'my-submissions', statusFilter],
    queryFn: () => api.getMySubmissions({ per_page: 50, status: statusFilter || undefined }),
    enabled: activeTab === 'my-submissions',
  })

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: number; comments?: string }) =>
      api.approveReview(reviewId, { comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
      setSelectedReview(null)
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: number; comments: string }) =>
      api.rejectReview(reviewId, { comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
      setSelectedReview(null)
    },
  })

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: (reviewId: number) => api.cancelReview(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    },
  })

  const reviews = activeTab === 'pending' ? pendingData?.items : submissionsData?.items
  const isLoading = activeTab === 'pending' ? pendingLoading : submissionsLoading
  const total = activeTab === 'pending' ? pendingData?.total : submissionsData?.total

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-900">Reviews</h1>
          <p className="text-slate-600">Review and approve document submissions</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab('pending')}
            className={`py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'pending'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Clock className="w-4 h-4" />
            Pending My Review
            {pendingData?.total ? (
              <span className="pill bg-amber-100 text-amber-700">
                {pendingData.total}
              </span>
            ) : null}
          </button>
          <button
            onClick={() => setActiveTab('my-submissions')}
            className={`py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'my-submissions'
                ? 'border-sky-600 text-sky-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Send className="w-4 h-4" />
            My Submissions
          </button>
        </nav>
      </div>

      {/* Status Filter (for My Submissions) */}
      {activeTab === 'my-submissions' && (
        <div className="flex items-center gap-4">
          <label className="text-sm text-slate-600">Filter by status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ReviewStatus | '')}
            className="select-field"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      )}

      {/* Reviews List */}
      <div className="surface-card rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">Loading reviews...</div>
        ) : !reviews?.length ? (
          <div className="p-8 text-center text-slate-500">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>
              {activeTab === 'pending'
                ? 'No documents pending your review'
                : 'You have not submitted any documents for review'}
            </p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Document
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  {activeTab === 'pending' ? 'Submitted By' : 'Reviewed By'}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {reviews.map((review) => (
                <tr key={review.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-slate-400" />
                      <div>
                        <Link
                          to={`/documents/${review.document_id}/fullscreen`}
                          className="text-sky-600 hover:text-sky-700 font-medium"
                        >
                          {review.document?.title || `Document #${review.document_id}`}
                        </Link>
                        {review.message && (
                          <p className="text-sm text-slate-500 flex items-center gap-1 mt-1">
                            <MessageSquare className="w-3 h-3" />
                            {review.message.length > 50
                              ? `${review.message.slice(0, 50)}...`
                              : review.message}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-sm text-slate-600">
                      <User className="w-4 h-4" />
                      {activeTab === 'pending'
                        ? review.submitter?.full_name || 'Unknown'
                        : review.reviewer?.full_name || '-'}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`pill ${
                        statusConfig[review.status].className
                      }`}
                    >
                      {statusConfig[review.status].icon}
                      {statusConfig[review.status].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      {new Date(review.submitted_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/documents/${review.document_id}/fullscreen`}
                        className="text-slate-600 hover:text-slate-800 text-sm"
                      >
                        View
                      </Link>
                      {activeTab === 'pending' && review.status === 'pending' && (
                        <button
                          onClick={() => setSelectedReview(review)}
                          className="btn-primary text-sm px-3 py-1"
                        >
                          Review
                        </button>
                      )}
                      {activeTab === 'my-submissions' && review.status === 'pending' && (
                        <button
                          onClick={() => {
                            if (confirm('Are you sure you want to cancel this submission?')) {
                              cancelMutation.mutate(review.id)
                            }
                          }}
                          disabled={cancelMutation.isPending}
                          className="text-rose-600 hover:text-rose-700 text-sm"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Footer with count */}
        {reviews && reviews.length > 0 && (
          <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-sm text-slate-600">
            Showing {reviews.length} of {total} reviews
          </div>
        )}
      </div>

      {/* Review Dialog */}
      {selectedReview && (
        <ReviewDialog
          review={selectedReview}
          onClose={() => setSelectedReview(null)}
          onApprove={(comments) =>
            approveMutation.mutate({ reviewId: selectedReview.id, comments })
          }
          onReject={(comments) =>
            rejectMutation.mutate({ reviewId: selectedReview.id, comments })
          }
          isLoading={approveMutation.isPending || rejectMutation.isPending}
        />
      )}
    </div>
  )
}
