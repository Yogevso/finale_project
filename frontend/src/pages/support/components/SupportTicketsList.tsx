import { formatDistanceToNow } from 'date-fns'
import { Filter, MessageSquareText, Trash2 } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { TableSkeleton } from '@/components/skeletons'
import type { SupportTicket, SupportTicketStatus, SupportTicketSummary } from '@/types/chat'

import { getSupportPriorityBadge, getSupportStatusColor } from '../constants'

interface SupportTicketsListProps {
  tickets: SupportTicket[]
  summary: SupportTicketSummary | null
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  statusFilter: SupportTicketStatus | ''
  onStatusFilterChange: (value: SupportTicketStatus | '') => void
  onOpenTicket: (ticketId: number) => void
  onDeleteTicket?: (ticketId: number) => void
}

export function SupportTicketsList({
  tickets,
  summary,
  isLoading,
  isError,
  onRetry,
  statusFilter,
  onStatusFilterChange,
  onOpenTicket,
  onDeleteTicket,
}: SupportTicketsListProps) {
  return (
    <div className="mx-4 space-y-4">
      {summary ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="surface-card rounded-xl p-4">
            <p className="helper-copy uppercase tracking-[0.18em]">Unread</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {summary.unread_count}
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Tickets with unread support notifications
            </p>
          </div>
          <div className="surface-card rounded-xl p-4">
            <p className="helper-copy uppercase tracking-[0.18em]">Customer Reply</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {summary.customer_reply_count}
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Tickets waiting on an agent reply
            </p>
          </div>
          <div className="surface-card rounded-xl p-4">
            <p className="helper-copy uppercase tracking-[0.18em]">Needs Attention</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {summary.needs_attention_count}
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Open or in-progress tickets with recent customer activity
            </p>
          </div>
        </div>
      ) : null}

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
            { header: '' },
          ]}
          gridTemplateColumns="minmax(5rem, 0.55fr) minmax(16rem, 1.8fr) minmax(12rem, 1.2fr) minmax(8rem, 0.8fr) minmax(8rem, 0.8fr) minmax(10rem, 0.9fr) minmax(4rem, 0.4fr)"
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
                  <div className="mt-1 flex flex-wrap items-center gap-1">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        ticket.feedback_id
                          ? 'bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-200'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                      }`}
                    >
                      {ticket.feedback_id ? 'Escalated from feedback' : 'Support ticket'}
                    </span>
                    {ticket.has_unread_activity ? (
                      <span className="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">
                        Unread
                      </span>
                    ) : null}
                    {ticket.awaiting_agent_reply ? (
                      <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                        Customer replied
                      </span>
                    ) : null}
                    {ticket.needs_attention ? (
                      <span className="inline-flex rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
                        Needs attention
                      </span>
                    ) : null}
                  </div>
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
              <div className="admin-table-cell flex items-center justify-center">
                {ticket.status === 'closed' && onDeleteTicket ? (
                  <button
                    type="button"
                    title="Delete closed ticket"
                    aria-label={`Delete ticket #${ticket.id}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm(`Delete ticket #${ticket.id}? This cannot be undone.`)) {
                        onDeleteTicket(ticket.id)
                      }
                    }}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                ) : null}
              </div>
            </>
          )}
        />
      )}
    </div>
  )
}
