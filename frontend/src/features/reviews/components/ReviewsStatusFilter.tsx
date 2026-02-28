import type { ReviewStatus } from '@/types'

type ReviewsStatusFilterProps = {
  statusFilter: ReviewStatus | ''
  onStatusFilterChange: (status: ReviewStatus | '') => void
}

export function ReviewsStatusFilter({
  statusFilter,
  onStatusFilterChange,
}: ReviewsStatusFilterProps) {
  return (
    <div className="flex items-center gap-4">
      <label className="text-sm text-slate-600">Filter by status:</label>
      <select
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value as ReviewStatus | '')}
        className="select-field"
      >
        <option value="">All</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="cancelled">Cancelled</option>
      </select>
    </div>
  )
}

