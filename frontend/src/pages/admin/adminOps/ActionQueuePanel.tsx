import { useCallback, useEffect, useState } from 'react'
import { CheckCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { FormField } from '@/components/form'
import { TableSkeleton } from '@/components/skeletons'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { extractApiErrorMessage } from '@/lib/toast'
import type { AdminAction } from '@/lib/api/adminOpsApi'
import { toast } from 'sonner'

export default function ActionQueuePanel() {
  const { user } = useAuth()
  const [actions, setActions] = useState<AdminAction[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [hasError, setHasError] = useState(false)

  const load = useCallback(() => {
    setHasError(false)
    setLoading(true)
    api.listAdminActions(filter || undefined)
      .then(setActions)
      .catch(() => setHasError(true))
      .finally(() => setLoading(false))
  }, [filter])

  useEffect(() => {
    load()
  }, [load])

  const handleReview = async (id: number, approved: boolean) => {
    const comment = approved ? undefined : prompt('Reason for rejection:') || undefined
    try {
      await api.reviewAdminAction(id, approved, comment)
      toast.success(approved ? 'Action approved' : 'Action rejected')
      load()
    } catch (error: unknown) {
      toast.error(extractApiErrorMessage(error, 'Review failed'))
    }
  }

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
      executed: 'bg-blue-100 text-blue-700',
    }
    return colors[status] || 'bg-slate-100 text-slate-700'
  }

  return (
    <div className="space-y-4">
      <div className="max-w-xs">
        <FormField label="Status filter" htmlFor="admin-action-filter">
          <select id="admin-action-filter" value={filter} onChange={(e) => setFilter(e.target.value)} className="select-field">
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          </select>
        </FormField>
      </div>

      {loading ? (
        <TableSkeleton rows={8} columns={5} />
      ) : hasError ? (
        <ErrorState
          title="Action queue unavailable"
          message="We could not load the admin action log."
          onRetry={load}
        />
      ) : actions.length === 0 ? (
        <EmptyState
          icon={<CheckCircle className="h-8 w-8" aria-hidden="true" />}
          title="No actions recorded"
          description="Admin approvals and executions will appear here once actions are queued."
        />
      ) : (
        <VirtualizedTable
          items={actions}
          ariaLabel="Admin actions"
          columns={[
            { header: 'Action' },
            { header: 'Requester' },
            { header: 'Status' },
            { header: 'Created' },
            { header: 'Review', headerClassName: 'text-right' },
          ]}
          gridTemplateColumns="minmax(18rem, 1.8fr) minmax(14rem, 1.1fr) minmax(8rem, 0.7fr) minmax(11rem, 0.9fr) minmax(12rem, 1fr)"
          estimateRowHeight={96}
          rowKey={(action) => action.id}
          renderRow={(action: AdminAction) => (
            <>
              <div className="admin-table-cell">
                <div className="space-y-1">
                  <div className="font-medium text-slate-900 dark:text-slate-100">
                    {action.action_type.replace(/_/g, ' ')}
                  </div>
                  {action.reason ? (
                    <p className="text-sm italic text-slate-600 dark:text-slate-300">
                      "{action.reason}"
                    </p>
                  ) : (
                    <p className="text-sm text-slate-400 dark:text-slate-500">No justification provided.</p>
                  )}
                </div>
              </div>
              <div className="admin-table-cell">
                <div className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                  <div>Requested by {action.requester_name || `#${action.requested_by}`}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {action.target_tenant_name ? `Target: ${action.target_tenant_name}` : 'Global action'}
                  </div>
                </div>
              </div>
              <div className="admin-table-cell">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(action.status)}`}>
                  {action.status}
                </span>
              </div>
              <div className="admin-table-cell text-xs text-slate-500 dark:text-slate-400">
                {new Date(action.created_at).toLocaleString()}
              </div>
              <div className="admin-table-cell">
                {action.status === 'pending' && action.requested_by !== user?.id ? (
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => handleReview(action.id, true)}
                      className="btn-success px-3 py-1.5 text-sm hover:scale-[1.02]"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleReview(action.id, false)}
                      className="btn-danger px-3 py-1.5 text-sm hover:scale-[1.02]"
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  <span className="block text-right text-xs text-slate-400 dark:text-slate-500">
                    {action.status === 'pending' ? 'Awaiting another reviewer' : 'Reviewed'}
                  </span>
                )}
              </div>
            </>
          )}
        />
      )}
    </div>
  )
}
