import type { CSSProperties } from 'react';
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
    <div className="reviews-table-shell">
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
        <div className="reviews-table-scroll">
          <table className="reviews-table" aria-label="Review queue list">
            <thead className="reviews-table-head">
              <tr>
                <th>Document</th>
                <th>{activeTab === 'pending' ? 'Submitted By' : 'Reviewer'}</th>
                <th>Status</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((review, index) =>
                (() => {
                  const displayStatus = getReviewDisplayStatus(review, activeTab);
                  const StatusIcon = reviewStatusConfig[displayStatus].icon;

                  return (
                    <tr
                      key={review.id}
                      className="reviews-table-row motion-enter-fade"
                      style={
                        {
                          '--enter-delay': `${Math.min(index, 7) * 28}ms`,
                        } as CSSProperties
                      }
                    >
                      <td className="reviews-table-cell">
                        <div className="flex items-start gap-3">
                          <span className="reviews-doc-icon" aria-hidden="true">
                            <FileText className="w-5 h-5" />
                          </span>
                          <div className="min-w-0">
                            <Link
                              to={`/documents/${review.document_id}/fullscreen`}
                              className="reviews-doc-link"
                            >
                              {review.document?.title || `Document #${review.document_id}`}
                            </Link>
                            {review.message && (
                              <p className="reviews-message-chip">
                                <MessageSquare className="w-3 h-3 shrink-0" />
                                {review.message.length > 50
                                  ? `${review.message.slice(0, 50)}...`
                                  : review.message}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="reviews-table-cell">
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <User className="w-4 h-4 text-slate-400" />
                          {activeTab === 'pending'
                            ? review.submitter?.full_name || 'Unknown'
                            : review.status === 'pending' &&
                                (review.requested_reviewers?.length || 0) > 0
                              ? (() => {
                                  const names = review.requested_reviewers!.map((user) => user.full_name)
                                  if (names.length <= 2) {
                                    return names.join(', ')
                                  }
                                  return `${names.slice(0, 2).join(', ')} +${names.length - 2}`
                                })()
                              : review.reviewer?.full_name || '-'}
                        </div>
                      </td>
                      <td className="reviews-table-cell">
                        <span
                          className={`pill reviews-status-pill ${reviewStatusConfig[displayStatus].className}`}
                        >
                          <StatusIcon className="w-4 h-4" />
                          {reviewStatusConfig[displayStatus].label}
                        </span>
                      </td>
                      <td className="reviews-table-cell">
                        <div className="inline-flex items-center gap-1.5 text-sm text-slate-600">
                          <Calendar className="w-4 h-4 text-slate-400" />
                          {new Date(review.submitted_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="reviews-table-cell reviews-table-cell-actions">
                        <div className="flex items-center justify-end gap-2">
                          {activeTab === 'pending' && review.status === 'pending' && (
                            <button
                              onClick={() => onOpenReview(review)}
                              className="btn-primary px-4 py-2 text-xs sm:text-sm"
                            >
                              {displayStatus === 'in_progress' ? 'Continue Review' : 'Review'}
                            </button>
                          )}
                          {activeTab === 'my-submissions' && review.status === 'pending' && (
                            <button
                              onClick={() => onCancelReview(review.id)}
                              disabled={cancelPending}
                              className="inline-flex items-center rounded-full border border-rose-200 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-rose-700 transition hover:bg-rose-50 hover:text-rose-800 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              Cancel
                            </button>
                          )}
                          {activeTab === 'my-submissions' && review.status === 'rejected' && (
                            <button
                              onClick={() => onOpenReview(review)}
                              className="inline-flex items-center rounded-full border border-sky-200 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-sky-700 transition hover:bg-sky-50 hover:text-sky-800"
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
        </div>
      )}

      {reviews && reviews.length > 0 && (
        <div className="reviews-table-footer">
          <span>
            Showing {reviews.length} of {total} reviews
          </span>
          <span className="reviews-footer-pill">
            {activeTab === 'pending' ? 'Queue View' : 'Submission View'}
          </span>
        </div>
      )}
    </div>
  );
}
