import { SlidersHorizontal } from 'lucide-react';

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
    <div className="reviews-status-panel">
      <div className="reviews-status-copy">
        <span className="reviews-status-icon" aria-hidden="true">
          <SlidersHorizontal className="h-4 w-4" />
        </span>
        <div>
          <label
            htmlFor="reviews-status-filter"
            className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400"
          >
            Filter by status
          </label>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-300">
            Focus your submission queue on one decision state.
          </p>
        </div>
      </div>
      <select
        id="reviews-status-filter"
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value as ReviewStatus | '')}
        className="select-field reviews-status-select"
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
