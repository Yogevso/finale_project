import { Activity, Clock3, FileSearch, Filter, X } from 'lucide-react';

import { ErrorState } from '@/components/ErrorState';
import ReviewDialog from '@/components/ReviewDialog';
import PageHeader from '@/components/PageHeader';
import {
  ReviewsStatusFilter,
  ReviewsTable,
  ReviewsTabs,
  useReviewsPageController,
} from '@/features/reviews';

export default function ReviewsPage() {
  const controller = useReviewsPageController();
  const pendingCount = controller.pendingData?.total || 0;
  const visibleRows = controller.reviews?.length || 0;
  const activeViewLabel = controller.activeTab === 'pending' ? 'Pending queue' : 'My submissions';
  const activeStatusLabel = controller.statusFilter
    ? controller.statusFilter.replace('_', ' ')
    : 'all statuses';

  return (
    <div className="page-stack">
      <PageHeader
        title="Reviews"
        subtitle="Review and approve submissions. Publishing is a separate step."
      />

      <section className="reviews-hero">
        <div className="reviews-hero-grid">
          <article className="reviews-hero-stat">
            <span className="reviews-stat-icon" aria-hidden="true">
              <Clock3 className="h-4 w-4" />
            </span>
            <div>
              <p className="reviews-stat-label">Pending Queue</p>
              <p className="reviews-stat-value">{pendingCount}</p>
            </div>
          </article>
          <article className="reviews-hero-stat">
            <span className="reviews-stat-icon" aria-hidden="true">
              <Activity className="h-4 w-4" />
            </span>
            <div>
              <p className="reviews-stat-label">Visible Rows</p>
              <p className="reviews-stat-value">{visibleRows}</p>
            </div>
          </article>
          <article className="reviews-hero-stat">
            <span className="reviews-stat-icon" aria-hidden="true">
              <Filter className="h-4 w-4" />
            </span>
            <div>
              <p className="reviews-stat-label">Current Lens</p>
              <p className="reviews-stat-value text-base capitalize">
                {controller.activeTab === 'my-submissions'
                  ? `${activeViewLabel} · ${activeStatusLabel}`
                  : activeViewLabel}
              </p>
            </div>
          </article>
        </div>

        <ReviewsTabs
          activeTab={controller.activeTab}
          pendingCount={pendingCount}
          onTabChange={controller.setActiveTab}
        />

        {controller.activeTab === 'my-submissions' && (
          <ReviewsStatusFilter
            statusFilter={controller.statusFilter}
            onStatusFilterChange={controller.setStatusFilter}
          />
        )}

        {controller.documentFilterId && (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-blue-200/80 bg-blue-50/60 p-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-blue-700">
              <FileSearch className="h-3.5 w-3.5" />
              Filtered to document #{controller.documentFilterId}
            </span>
            <button
              type="button"
              onClick={controller.clearDocumentFilter}
              className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 transition hover:border-slate-400 hover:text-slate-800"
            >
              <X className="h-3.5 w-3.5" />
              Clear filter
            </button>
          </div>
        )}
      </section>

      {controller.isError ? (
        <ErrorState
          title={
            controller.activeTab === 'pending'
              ? 'Reviews could not be loaded'
              : 'Submissions could not be loaded'
          }
          message={
            controller.activeTab === 'pending'
              ? 'We could not fetch the current review queue.'
              : 'We could not fetch your review submissions.'
          }
          onRetry={() => void controller.refetchCurrent()}
        />
      ) : (
        <ReviewsTable
          activeTab={controller.activeTab}
          reviews={controller.reviews}
          isLoading={controller.isLoading}
          total={controller.total}
          cancelPending={controller.cancelMutation.isPending}
          onOpenReview={controller.openSelectedReview}
          onCancelReview={controller.handleCancelReview}
        />
      )}

      {controller.selectedReview && (
        <ReviewDialog
          review={controller.selectedReview}
          onClose={controller.closeSelectedReview}
          onApprove={controller.approveSelectedReview}
          onReject={controller.rejectSelectedReview}
          isLoading={controller.dialogLoading}
        />
      )}
    </div>
  );
}
