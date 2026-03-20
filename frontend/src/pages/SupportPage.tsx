/**
 * SupportPage â€” agent/manager support ticket dashboard (X1-093 to X1-098)
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import {
  ArrowLeft,
  ArrowRightLeft,
  Eye,
  Filter,
  MessageSquareText,
  Search,
  Send,
  UserPlus,
  X,
} from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import { VirtualizedTable } from '@/components/VirtualizedTable'
import { SubmitButton, TextArea } from '@/components/form'
import { CardSkeleton, ListSkeleton, TableSkeleton } from '@/components/skeletons'
import { useFocusTrap } from '@/hooks/useAccessibility'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type {
  SupportTicket,
  SupportTicketDetail,
  SupportTicketPriority,
  SupportTicketStatus,
} from '@/types/chat'

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-200',
  in_progress: 'bg-sky-100 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-950/30 dark:text-green-200',
  closed: 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300',
}

const PRIORITY_BADGE: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-300',
  normal: 'bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200',
  high: 'bg-orange-50 text-orange-700 dark:bg-orange-950/30 dark:text-orange-200',
  urgent: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-200',
}

export default function SupportPage() {
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<SupportTicketStatus | ''>('')

  const ticketsQuery = useQuery({
    queryKey: ['supportTickets', statusFilter],
    queryFn: () =>
      api.getSupportTickets({
        status: statusFilter || undefined,
        page: 1,
        page_size: 50,
      }),
  })

  const ticketQuery = useQuery({
    queryKey: ['supportTicket', activeTicketId],
    queryFn: () => (activeTicketId ? api.getSupportTicket(activeTicketId) : Promise.reject()),
    enabled: !!activeTicketId,
  })

  const tickets = ticketsQuery.data?.items ?? []

  if (activeTicketId && ticketQuery.isLoading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage customer support tickets" />
        <div className="mx-4 mb-4">
          <ListSkeleton rows={5} />
        </div>
      </div>
    )
  }

  if (activeTicketId && ticketQuery.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage customer support tickets" />
        <div className="mx-4 mb-4">
          <ErrorState
            title="Ticket could not be loaded"
            message="We could not load the selected support ticket."
            onRetry={() => void ticketQuery.refetch()}
          />
        </div>
      </div>
    )
  }

  if (activeTicketId && ticketQuery.data) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage customer support tickets" />
        <div className="mx-4 mb-4">
          <TicketDetailView ticket={ticketQuery.data} onBack={() => setActiveTicketId(null)} />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <PageHeader title="Support" subtitle="Manage customer support tickets" />

      <div className="mx-4 space-y-4">
        <div className="surface-card flex items-center gap-3 rounded-xl p-3">
          <Filter className="h-4 w-4 text-gray-400 dark:text-slate-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as SupportTicketStatus | '')}
            className="select-field max-w-xs"
            aria-label="Filter tickets by status"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <span className="text-sm text-gray-500 dark:text-slate-400">{tickets.length} ticket(s)</span>
        </div>

        {ticketsQuery.isLoading ? (
          <TableSkeleton rows={6} columns={6} />
        ) : ticketsQuery.isError ? (
          <ErrorState
            title="Tickets could not be loaded"
            message="We could not fetch the support queue."
            onRetry={() => void ticketsQuery.refetch()}
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
            onRowClick={(ticket) => setActiveTicketId(ticket.id)}
            renderRow={(ticket: SupportTicket) => (
              <>
                <div className="admin-table-cell text-sm text-slate-500 dark:text-slate-400">
                  #{ticket.id}
                </div>
                <div className="admin-table-cell text-sm font-medium text-slate-900 dark:text-slate-100">
                  {ticket.subject}
                </div>
                <div className="admin-table-cell text-sm text-slate-600 dark:text-slate-300">
                  {ticket.customer_full_name || '-'}
                </div>
                <div className="admin-table-cell">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_BADGE[ticket.priority]}`}
                  >
                    {ticket.priority}
                  </span>
                </div>
                <div className="admin-table-cell">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[ticket.status]}`}
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
    </div>
  )
}

/* ---- Ticket Detail View (Agent) ---- */

function TicketDetailView({
  ticket,
  onBack,
}: {
  ticket: SupportTicketDetail
  onBack: () => void
}) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [message, setMessage] = useState('')
  const [messageError, setMessageError] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [showAssign, setShowAssign] = useState(false)
  const [showHandoff, setShowHandoff] = useState(false)
  const [showCanned, setShowCanned] = useState(false)
  const [cannedSearch, setCannedSearch] = useState('')

  const viewersQuery = useQuery({
    queryKey: ['ticketViewers', ticket.id],
    queryFn: () => api.getTicketViewers(ticket.id),
    refetchInterval: 15000,
  })
  const viewerIds = viewersQuery.data?.viewer_ids ?? []
  const otherViewers = viewerIds.filter((id) => id !== user?.id)

  const sendMutation = useMutation({
    mutationFn: (data: { content: string; is_internal_note: boolean }) =>
      api.sendSupportTicketMessage(ticket.id, data),
    onSuccess: () => {
      setMessage('')
      setMessageError('')
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
    },
    onError: (error: unknown) => {
      toast.error('Failed to send message', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: { status?: SupportTicketStatus; priority?: SupportTicketPriority }) =>
      api.updateSupportTicket(ticket.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
      queryClient.invalidateQueries({ queryKey: ['supportTickets'] })
    },
    onError: (error: unknown) => {
      toast.error('Failed to update ticket', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const unassignMutation = useMutation({
    mutationFn: (agentId: number) => api.unassignSupportAgent(ticket.id, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
    },
    onError: (error: unknown) => {
      toast.error('Failed to unassign agent', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const handleSend = () => {
    if (!message.trim()) {
      setMessageError('A reply message is required.')
      return
    }
    sendMutation.mutate({ content: message.trim(), is_internal_note: isInternal })
  }

  const cannedQuery = useQuery({
    queryKey: ['cannedResponses', cannedSearch],
    queryFn: () => api.getCannedResponses({ search: cannedSearch || undefined }),
    enabled: showCanned,
  })

  const insertCanned = (content: string) => {
    const resolved = content
      .replace(/\{\{customer_name\}\}/g, ticket.customer_full_name || 'Customer')
      .replace(/\{\{ticket_id\}\}/g, String(ticket.id))
      .replace(/\{\{agent_name\}\}/g, user?.full_name || 'Agent')
    setMessage((prev) => (prev ? `${prev}\n${resolved}` : resolved))
    setMessageError('')
    setShowCanned(false)
    setCannedSearch('')
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={onBack}
          className="mt-1 rounded-lg p-2 text-gray-400 hover:bg-gray-100 dark:text-slate-500 dark:hover:bg-slate-800"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">{ticket.subject}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span>#{ticket.id}</span>
            <span>·</span>
            <span>by {ticket.customer_full_name || 'Unknown'}</span>
            <span>·</span>
            <span>{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowHandoff(true)}
          className="btn-warning px-3 py-1.5 text-sm"
        >
          <ArrowRightLeft className="h-4 w-4" /> Handoff
        </button>
        <button
          type="button"
          onClick={() => setShowAssign(true)}
          className="btn-secondary px-3 py-1.5 text-sm"
        >
          <UserPlus className="h-4 w-4" /> Assign
        </button>
      </div>

      <div className="surface-card flex flex-wrap items-center gap-3 rounded-xl p-3">
        <label htmlFor="ticket-status" className="text-xs font-medium text-gray-500 dark:text-slate-400">
          Status:
        </label>
        <select
          id="ticket-status"
          value={ticket.status}
          onChange={(e) => updateMutation.mutate({ status: e.target.value as SupportTicketStatus })}
          className="select-field w-auto min-w-[9rem]"
        >
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>

        <label htmlFor="ticket-priority" className="ml-4 text-xs font-medium text-gray-500 dark:text-slate-400">
          Priority:
        </label>
        <select
          id="ticket-priority"
          value={ticket.priority}
          onChange={(e) => updateMutation.mutate({ priority: e.target.value as SupportTicketPriority })}
          className="select-field w-auto min-w-[9rem]"
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>

        {ticket.assignments.length > 0 ? (
          <div className="ml-auto flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
            <span>Assigned:</span>
            {ticket.assignments.map((assignment) => (
              <span
                key={assignment.id}
                className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2 py-0.5 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200"
              >
                {assignment.agent_full_name || `Agent #${assignment.agent_id}`}
                {assignment.is_primary ? (
                  <span className="text-[9px] text-sky-500 dark:text-sky-300">(primary)</span>
                ) : null}
                <button
                  type="button"
                  onClick={() => unassignMutation.mutate(assignment.agent_id)}
                  className="ml-0.5 rounded-full p-0.5 text-sky-400 hover:bg-sky-100 hover:text-sky-700 dark:text-sky-300 dark:hover:bg-sky-900/40 dark:hover:text-sky-100"
                  title="Unassign"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        ) : null}

        {otherViewers.length > 0 ? (
          <div className="flex items-center gap-1.5 text-xs text-emerald-600">
            <Eye className="h-3.5 w-3.5" />
            <span>
              {otherViewers.length} other agent{otherViewers.length > 1 ? 's' : ''} viewing
            </span>
          </div>
        ) : null}
      </div>

      <div className="surface-card rounded-xl">
        <div className="max-h-[50vh] space-y-3 overflow-y-auto p-4">
          {ticket.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.sender_id === user?.id ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                  msg.is_internal_note
                    ? 'border border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-100'
                    : msg.sender_id === user?.id
                      ? 'bg-sky-600 text-white'
                      : 'bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-slate-100'
                }`}
              >
                <div className="mb-0.5 flex items-center gap-1.5 text-xs opacity-75">
                  <span className="font-medium">{msg.sender_full_name || 'Unknown'}</span>
                  {msg.is_internal_note ? <span className="italic">(internal note)</span> : null}
                </div>
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                <p className="mt-1 text-[10px] opacity-60">
                  {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-2 border-t border-gray-200 p-3 dark:border-slate-800">
          <div className="flex items-center gap-3 text-xs">
            <label className="flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={isInternal}
                onChange={(e) => setIsInternal(e.target.checked)}
                className="rounded border-gray-300 dark:border-slate-700"
              />
              <span className="font-medium text-amber-700 dark:text-amber-200">Internal note</span>
            </label>
            <div className="relative ml-auto">
              <button
                type="button"
                onClick={() => setShowCanned(!showCanned)}
                className="flex items-center gap-1 rounded-lg border border-gray-300 px-2 py-1 text-xs text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                title="Insert canned response"
              >
                <MessageSquareText className="h-3.5 w-3.5" />
                Templates
              </button>
              {showCanned ? (
                <div className="dropdown-menu absolute bottom-8 right-0 z-50 w-80 dark:bg-slate-900">
                  <div className="border-b border-gray-100 p-2 dark:border-slate-800">
                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400 dark:text-slate-500" />
                      <input
                        type="text"
                        placeholder="Search templates..."
                        value={cannedSearch}
                        onChange={(e) => setCannedSearch(e.target.value)}
                        className="input-field py-1.5 pl-8 pr-3 text-xs"
                      />
                    </div>
                  </div>
                  <div className="max-h-48 overflow-y-auto p-1">
                    {(cannedQuery.data?.items ?? []).length === 0 ? (
                      cannedQuery.isLoading ? (
                        <div className="px-2 py-2">
                          <CardSkeleton count={2} />
                        </div>
                      ) : (
                          <p className="px-3 py-4 text-center text-xs text-gray-400 dark:text-slate-500">
                            No templates found
                          </p>
                      )
                    ) : (
                      (cannedQuery.data?.items ?? []).map((cannedResponse) => (
                        <button
                          key={cannedResponse.id}
                          type="button"
                          onClick={() => insertCanned(cannedResponse.content)}
                          className="w-full rounded-lg px-3 py-2 text-left transition-colors hover:bg-sky-50 dark:hover:bg-sky-950/30"
                        >
                          <p className="text-xs font-medium text-gray-900 dark:text-slate-100">
                            {cannedResponse.title}
                          </p>
                          {cannedResponse.category ? (
                            <span className="text-[10px] text-gray-400 dark:text-slate-500">
                              {cannedResponse.category}
                            </span>
                          ) : null}
                          <p className="mt-0.5 line-clamp-2 text-[11px] text-gray-500 dark:text-slate-400">
                            {cannedResponse.content}
                          </p>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1">
              <TextArea
                label="Reply"
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value)
                  if (messageError) {
                    setMessageError('')
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder={
                  isInternal
                    ? 'Internal note (not visible to customer)...'
                    : 'Reply to customer...'
                }
                rows={2}
                maxLength={2000}
                error={messageError}
                required
              />
            </div>
            <SubmitButton
              type="button"
              onClick={handleSend}
              disabled={sendMutation.isPending || !message.trim()}
              isLoading={sendMutation.isPending}
              loadingText="Sending..."
              className="min-w-[9rem]"
            >
              <Send className="h-4 w-4" />
              Send reply
            </SubmitButton>
          </div>
        </div>
      </div>

      {showAssign ? <AssignAgentModal ticketId={ticket.id} onClose={() => setShowAssign(false)} /> : null}
      {showHandoff ? <HandoffModal ticketId={ticket.id} onClose={() => setShowHandoff(false)} /> : null}
    </div>
  )
}

/* ---- Assign Agent Modal ---- */

function AssignAgentModal({
  ticketId,
  onClose,
}: {
  ticketId: number
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')

  const { data: users = [] } = useQuery({
    queryKey: ['users', { search }],
    queryFn: () => api.getUsers({ search: search || undefined, is_active: true }),
  })

  const agents = users.filter((u) => u.role !== 'customer')

  const assignMutation = useMutation({
    mutationFn: (agentId: number) =>
      api.assignSupportAgent(ticketId, { agent_id: agentId, is_primary: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticketId] })
      onClose()
    },
  })

  const { containerRef: assignRef } = useFocusTrap(onClose)

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close assign agent dialog"
      />
      <div
        ref={assignRef}
        role="dialog"
        aria-modal="true"
        aria-label="Assign Agent"
        className="modal-content relative w-full max-w-sm"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Assign Agent</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200"
            aria-label="Close assign agent dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4">
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field mb-3"
          />
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {agents.map((agent) => (
              <button
                type="button"
                key={agent.id}
                onClick={() => assignMutation.mutate(agent.id)}
                disabled={assignMutation.isPending}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-slate-800"
              >
                <div className="h-7 w-7 rounded-full bg-gray-200 text-center text-xs leading-7 text-gray-600 dark:bg-slate-700 dark:text-slate-300">
                  {(agent.full_name || agent.email).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-slate-100">{agent.full_name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{agent.role}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---- Handoff Modal (X1-102) ---- */

function HandoffModal({
  ticketId,
  onClose,
}: {
  ticketId: number
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [note, setNote] = useState('')
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null)

  const { data: users = [] } = useQuery({
    queryKey: ['users', { search }],
    queryFn: () => api.getUsers({ search: search || undefined, is_active: true }),
  })

  const agents = users.filter((u) => u.role !== 'customer')

  const handoffMutation = useMutation({
    mutationFn: () => api.handoffTicket(ticketId, selectedAgentId!, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticketId] })
      onClose()
    },
  })

  const { containerRef: handoffRef } = useFocusTrap(onClose)

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close handoff dialog"
      />
      <div
        ref={handoffRef}
        role="dialog"
        aria-modal="true"
        aria-label="Handoff Ticket"
        className="modal-content relative w-full max-w-sm"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Handoff Ticket</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-200"
            aria-label="Close handoff dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-3 p-4">
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field"
          />
          <div className="max-h-36 space-y-1 overflow-y-auto">
            {agents.map((agent) => (
              <button
                type="button"
                key={agent.id}
                onClick={() => setSelectedAgentId(agent.id)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  selectedAgentId === agent.id
                    ? 'bg-orange-50 ring-1 ring-orange-300 dark:bg-orange-950/30 dark:ring-orange-900/70'
                    : 'hover:bg-gray-50 dark:hover:bg-slate-800'
                }`}
              >
                <div className="h-7 w-7 rounded-full bg-gray-200 text-center text-xs leading-7 text-gray-600 dark:bg-slate-700 dark:text-slate-300">
                  {(agent.full_name || agent.email).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-slate-100">{agent.full_name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{agent.role}</p>
                </div>
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Handoff note (optional)..."
            rows={2}
            className="input-field min-h-[5rem] resize-none"
          />
          <button
            type="button"
            onClick={() => handoffMutation.mutate()}
            disabled={!selectedAgentId || handoffMutation.isPending}
            className="w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600 disabled:opacity-50"
          >
            {handoffMutation.isPending ? 'Handing off...' : 'Confirm Handoff'}
          </button>
        </div>
      </div>
    </div>
  )
}
