import { Calendar, FileText, MessageSquare, User } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { TableSkeleton } from '@/components/skeletons';
import type { ReviewRequest } from '@/types';

import { getReviewDisplayStatus, reviewStatusConfig, type ReviewsTabType } from '../constants';

type ReviewsTableProps = {
  activeTab: ReviewsTabType;
  reviews: ReviewRequest[] | undefined;
  isLoading: boolean;
  total: number | undefined;
  cancelPending: boolean;
  onOpenReview: (review: ReviewRequest) => void;
  onCancelReview: (reviewId: number) => void;
};

export function ReviewsTable({
  activeTab,
  reviews,
  isLoading,
  total,
  cancelPending,
  onOpenReview,
  onCancelReview,
}: ReviewsTableProps) {
  return (
    <div className="surface-card rounded-2xl overflow-hidden">
      {isLoading ? (
        <TableSkeleton rows={6} columns={5} />
      ) : !reviews?.length ? (
        <div className="p-8">
          <EmptyState
            icon={<FileText className="h-8 w-8" aria-hidden="true" />}
            title={activeTab === 'pending' ? 'No pending reviews' : 'No review submissions yet'}
            description={
              activeTab === 'pending'
                ? 'Documents that need your review will appear here.'
                : 'Your submitted review requests will appear here once you send one.'
            }
          />
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
            {reviews.map((review) =>
              (() => {
                const displayStatus = getReviewDisplayStatus(review, activeTab);
                const StatusIcon = reviewStatusConfig[displayStatus].icon;
                return (
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
                      <span className={`pill ${reviewStatusConfig[displayStatus].className}`}>
                        <StatusIcon className="w-4 h-4" />
                        {reviewStatusConfig[displayStatus].label}
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
                        {activeTab === 'pending' && review.status === 'pending' && (
                          <button
                            onClick={() => onOpenReview(review)}
                            className="btn-primary text-sm px-3 py-1"
                          >
                            {displayStatus === 'in_progress' ? 'Continue Review' : 'Review'}
                          </button>
                        )}
                        {activeTab === 'my-submissions' && review.status === 'pending' && (
                          <button
                            onClick={() => onCancelReview(review.id)}
                            disabled={cancelPending}
                            className="text-rose-600 hover:text-rose-700 text-sm"
                          >
                            Cancel
                          </button>
                        )}
                        {activeTab === 'my-submissions' && review.status === 'rejected' && (
                          <button
                            onClick={() => onOpenReview(review)}
                            className="text-sky-600 hover:text-sky-700 text-sm font-medium"
                          >
                            Feedback
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })()
            )}
          </tbody>
        </table>
      )}

      {reviews && reviews.length > 0 && (
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-sm text-slate-600">
          Showing {reviews.length} of {total} reviews
        </div>
      )}
    </div>
  );
}
