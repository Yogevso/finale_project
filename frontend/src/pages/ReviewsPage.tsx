import { ErrorState } from '@/components/ErrorState'
import ReviewDialog from '@/components/ReviewDialog'
import PageHeader from '@/components/PageHeader'
import {
  ReviewsStatusFilter,
  ReviewsTable,
  ReviewsTabs,
  useReviewsPageController,
} from '@/features/reviews'

export default function ReviewsPage() {
  const controller = useReviewsPageController()

  return (
    <div className="page-stack">
      <PageHeader
        title="Reviews"
        subtitle="Review and approve submissions. Publishing is a separate step."
      />

      <ReviewsTabs
        activeTab={controller.activeTab}
        pendingCount={controller.pendingData?.total || 0}
        onTabChange={controller.setActiveTab}
      />

      {controller.activeTab === 'my-submissions' && (
        <ReviewsStatusFilter
          statusFilter={controller.statusFilter}
          onStatusFilterChange={controller.setStatusFilter}
        />
      )}

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
  )
}
