import type { ReviewStatus } from '@/types';

type ReviewsStatusFilterProps = {
  statusFilter: ReviewStatus | '';
  onStatusFilterChange: (status: ReviewStatus | '') => void;
};

export function ReviewsStatusFilter({
  statusFilter,
  onStatusFilterChange,
}: ReviewsStatusFilterProps) {
  return (
    <div className="surface-card flex flex-wrap items-center gap-3 rounded-2xl p-4">
      <label
        htmlFor="reviews-status-filter"
        className="helper-copy font-medium uppercase tracking-wide"
      >
        Filter by status
      </label>
      <select
        id="reviews-status-filter"
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value as ReviewStatus | '')}
        className="select-field max-w-[220px]"
      >
        <option value="">All</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Pending editor</option>
        <option value="cancelled">Cancelled</option>
      </select>
    </div>
  );
}
