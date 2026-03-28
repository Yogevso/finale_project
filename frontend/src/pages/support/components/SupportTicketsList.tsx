import { formatDistanceToNow } from 'date-fns'
import { Filter, MessageSquareText } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { TableSkeleton } from '@/components/skeletons'
import type { SupportTicket, SupportTicketStatus } from '@/types/chat'

import { getSupportPriorityBadge, getSupportStatusColor } from '../constants'

interface SupportTicketsListProps {
  tickets: SupportTicket[]
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  statusFilter: SupportTicketStatus | ''
  onStatusFilterChange: (value: SupportTicketStatus | '') => void
  onOpenTicket: (ticketId: number) => void
}

export function SupportTicketsList({
  tickets,
  isLoading,
  isError,
  onRetry,
  statusFilter,
  onStatusFilterChange,
  onOpenTicket,
}: SupportTicketsListProps) {
  return (
    <div className="mx-4 space-y-4">
      <div className="surface-card flex items-center gap-3 rounded-xl p-3">
        <Filter className="h-4 w-4 text-gray-400 dark:text-slate-500" />
        <select
          value={statusFilter}
          onChange={(event) => onStatusFilterChange(event.target.value as SupportTicketStatus | '')}
          className="select-field max-w-xs"
          aria-label="Filter tickets by status"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <span className="text-sm text-gray-500 dark:text-slate-400">
          {tickets.length} ticket(s)
        </span>
      </div>

      {isLoading ? (
        <TableSkeleton rows={6} columns={6} />
      ) : isError ? (
        <ErrorState
          title="Tickets could not be loaded"
          message="We could not fetch the support queue."
          onRetry={onRetry}
        />
      ) : tickets.length === 0 ? (
        <EmptyState
          icon={<MessageSquareText className="h-8 w-8" aria-hidden="true" />}
          title="No tickets found"
          description="Try a different status filter or check back when new conversations arrive."
        />
      ) : (
        <VirtualizedTable
          items={tickets}
          ariaLabel="Support tickets"
          columns={[
            { header: 'ID' },
            { header: 'Subject' },
            { header: 'Customer' },
            { header: 'Priority' },
            { header: 'Status' },
            { header: 'Created' },
          ]}
          gridTemplateColumns="minmax(5rem, 0.55fr) minmax(16rem, 1.8fr) minmax(12rem, 1.2fr) minmax(8rem, 0.8fr) minmax(8rem, 0.8fr) minmax(10rem, 0.9fr)"
          estimateRowHeight={68}
          rowKey={(ticket) => ticket.id}
          onRowClick={(ticket) => onOpenTicket(ticket.id)}
          renderRow={(ticket) => (
            <>
              <div className="admin-table-cell text-sm text-slate-500 dark:text-slate-400">
                #{ticket.id}
              </div>
              <div className="admin-table-cell text-sm font-medium text-slate-900 dark:text-slate-100">
                <div className="min-w-0">
                  <div className="truncate">{ticket.subject}</div>
                  <span
                    className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      ticket.feedback_id
                        ? 'bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-200'
                        : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                    }`}
                  >
                    {ticket.feedback_id ? 'Feedback conversation' : 'Support ticket'}
                  </span>
                </div>
              </div>
              <div className="admin-table-cell text-sm text-slate-600 dark:text-slate-300">
                {ticket.customer_full_name || '-'}
              </div>
              <div className="admin-table-cell">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${getSupportPriorityBadge(ticket.priority)}`}
                >
                  {ticket.priority}
                </span>
              </div>
              <div className="admin-table-cell">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${getSupportStatusColor(ticket.status)}`}
                >
                  {ticket.status.replace('_', ' ')}
                </span>
              </div>
              <div className="admin-table-cell text-xs text-slate-500 dark:text-slate-400">
                {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}
              </div>
            </>
          )}
        />
      )}
    </div>
  )
}
