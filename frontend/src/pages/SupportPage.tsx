/**
 * SupportPage — agent/manager support ticket dashboard (X1-093 to X1-098)
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDistanceToNow } from 'date-fns'
import {
  ArrowLeft,
  Send,
  Filter,
  UserPlus,
  X,
  MessageSquareText,
  Search,
  ArrowRightLeft,
  Eye,
} from 'lucide-react'
import PageHeader from '@/components/PageHeader'
import { useFocusTrap } from '@/hooks/useAccessibility'
import type {
  SupportTicket,
  SupportTicketDetail,
  SupportTicketStatus,
  SupportTicketPriority,
} from '@/types/chat'

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-700',
}

const PRIORITY_BADGE: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600',
  normal: 'bg-blue-50 text-blue-700',
  high: 'bg-orange-50 text-orange-700',
  urgent: 'bg-red-50 text-red-700',
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

  if (activeTicketId && ticketQuery.data) {
    return (
      <div className="space-y-4">
        <PageHeader title="Support" subtitle="Manage customer support tickets" />
        <div className="mx-4 mb-4">
          <TicketDetailView
            ticket={ticketQuery.data}
            onBack={() => setActiveTicketId(null)}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Support" subtitle="Manage customer support tickets" />

      <div className="mx-4 space-y-4">
        {/* Filters */}
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as SupportTicketStatus | '')}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <span className="text-sm text-gray-500">{tickets.length} ticket(s)</span>
        </div>

        {/* Ticket table */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Subject</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Customer</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Priority</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {tickets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                    No tickets found
                  </td>
                </tr>
              ) : (
                tickets.map((t: SupportTicket) => (
                  <tr
                    key={t.id}
                    onClick={() => setActiveTicketId(t.id)}
                    className="cursor-pointer transition-colors hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 text-sm text-gray-500">#{t.id}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{t.subject}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{t.customer_full_name || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_BADGE[t.priority]}`}>
                        {t.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[t.status]}`}>
                        {t.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
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
  const [message, setMessage] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [showAssign, setShowAssign] = useState(false)
  const [showHandoff, setShowHandoff] = useState(false)
  const [showCanned, setShowCanned] = useState(false)
  const [cannedSearch, setCannedSearch] = useState('')

  // Poll viewers every 15s (X1-100)
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
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: { status?: SupportTicketStatus; priority?: SupportTicketPriority }) =>
      api.updateSupportTicket(ticket.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
      queryClient.invalidateQueries({ queryKey: ['supportTickets'] })
    },
  })

  const unassignMutation = useMutation({
    mutationFn: (agentId: number) => api.unassignSupportAgent(ticket.id, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticket.id] })
    },
  })

  const handleSend = () => {
    if (!message.trim()) return
    sendMutation.mutate({ content: message.trim(), is_internal_note: isInternal })
  }

  const cannedQuery = useQuery({
    queryKey: ['cannedResponses', cannedSearch],
    queryFn: () => api.getCannedResponses({ search: cannedSearch || undefined }),
    enabled: showCanned,
  })

  const insertCanned = (content: string) => {
    // Replace template variables (X1-106)
    const resolved = content
      .replace(/\{\{customer_name\}\}/g, ticket.customer_full_name || 'Customer')
      .replace(/\{\{ticket_id\}\}/g, String(ticket.id))
      .replace(/\{\{agent_name\}\}/g, user?.full_name || 'Agent')
    setMessage((prev) => (prev ? prev + '\n' + resolved : resolved))
    setShowCanned(false)
    setCannedSearch('')
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <button onClick={onBack} className="mt-1 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-gray-900">{ticket.subject}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span>#{ticket.id}</span>
            <span>·</span>
            <span>by {ticket.customer_full_name || 'Unknown'}</span>
            <span>·</span>
            <span>{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</span>
          </div>
        </div>
        <button
          onClick={() => setShowHandoff(true)}
          className="flex items-center gap-1.5 rounded-lg border border-orange-300 px-3 py-1.5 text-sm text-orange-600 hover:bg-orange-50"
        >
          <ArrowRightLeft className="h-4 w-4" /> Handoff
        </button>
        <button
          onClick={() => setShowAssign(true)}
          className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          <UserPlus className="h-4 w-4" /> Assign
        </button>
      </div>

      {/* Status/priority controls */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white p-3">
        <label className="text-xs font-medium text-gray-500">Status:</label>
        <select
          value={ticket.status}
          onChange={(e) => updateMutation.mutate({ status: e.target.value as SupportTicketStatus })}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>

        <label className="ml-4 text-xs font-medium text-gray-500">Priority:</label>
        <select
          value={ticket.priority}
          onChange={(e) => updateMutation.mutate({ priority: e.target.value as SupportTicketPriority })}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>

        {ticket.assignments.length > 0 && (
          <div className="ml-auto flex items-center gap-1 text-xs text-gray-500">
            <span>Assigned:</span>
            {ticket.assignments.map((a) => (
              <span key={a.id} className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-blue-700">
                {a.agent_full_name || `Agent #${a.agent_id}`}
                {a.is_primary && <span className="text-[9px] text-blue-500">(primary)</span>}
                <button
                  onClick={() => unassignMutation.mutate(a.agent_id)}
                  className="ml-0.5 rounded-full p-0.5 text-blue-400 hover:bg-blue-100 hover:text-blue-700"
                  title="Unassign"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Viewers indicator (X1-100) */}
        {otherViewers.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-emerald-600">
            <Eye className="h-3.5 w-3.5" />
            <span>{otherViewers.length} other agent{otherViewers.length > 1 ? 's' : ''} viewing</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="max-h-[50vh] overflow-y-auto p-4 space-y-3">
          {ticket.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.sender_id === user?.id ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                  msg.is_internal_note
                    ? 'border border-amber-200 bg-amber-50 text-amber-900'
                    : msg.sender_id === user?.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="mb-0.5 flex items-center gap-1.5 text-xs opacity-75">
                  <span className="font-medium">{msg.sender_full_name || 'Unknown'}</span>
                  {msg.is_internal_note && <span className="italic">(internal note)</span>}
                </div>
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                <p className="mt-1 text-[10px] opacity-60">
                  {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Reply */}
        <div className="border-t border-gray-200 p-3 space-y-2">
          <div className="flex items-center gap-3 text-xs">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={isInternal}
                onChange={(e) => setIsInternal(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-amber-700 font-medium">Internal note</span>
            </label>
            {/* Canned response selector (X1-105) */}
            <div className="relative ml-auto">
              <button
                onClick={() => setShowCanned(!showCanned)}
                className="flex items-center gap-1 rounded-lg border border-gray-300 px-2 py-1 text-xs text-gray-500 hover:bg-gray-50 hover:text-gray-700"
                title="Insert canned response"
              >
                <MessageSquareText className="h-3.5 w-3.5" />
                Templates
              </button>
              {showCanned && (
                <div className="absolute bottom-8 right-0 z-50 w-80 rounded-xl border border-gray-200 bg-white shadow-xl">
                  <div className="border-b border-gray-100 p-2">
                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search templates..."
                        value={cannedSearch}
                        onChange={(e) => setCannedSearch(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 pl-8 pr-3 py-1.5 text-xs focus:border-blue-500 focus:outline-none"
                        autoFocus
                      />
                    </div>
                  </div>
                  <div className="max-h-48 overflow-y-auto p-1">
                    {(cannedQuery.data?.items ?? []).length === 0 ? (
                      <p className="px-3 py-4 text-center text-xs text-gray-400">
                        {cannedQuery.isLoading ? 'Loading...' : 'No templates found'}
                      </p>
                    ) : (
                      (cannedQuery.data?.items ?? []).map((cr) => (
                        <button
                          key={cr.id}
                          onClick={() => insertCanned(cr.content)}
                          className="w-full rounded-lg px-3 py-2 text-left hover:bg-blue-50 transition-colors"
                        >
                          <p className="text-xs font-medium text-gray-900">{cr.title}</p>
                          {cr.category && (
                            <span className="text-[10px] text-gray-400">{cr.category}</span>
                          )}
                          <p className="mt-0.5 text-[11px] text-gray-500 line-clamp-2">{cr.content}</p>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-end gap-2">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={isInternal ? 'Internal note (not visible to customer)...' : 'Reply to customer...'}
              rows={2}
              className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <button
              onClick={handleSend}
              disabled={sendMutation.isPending || !message.trim()}
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {showAssign && (
        <AssignAgentModal
          ticketId={ticket.id}
          onClose={() => setShowAssign(false)}
        />
      )}
      {showHandoff && (
        <HandoffModal
          ticketId={ticket.id}
          onClose={() => setShowHandoff(false)}
        />
      )}
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

  // Only show internal users (non-customer)
  const agents = users.filter((u) => u.role !== 'customer')

  const assignMutation = useMutation({
    mutationFn: (agentId: number) =>
      api.assignSupportAgent(ticketId, { agent_id: agentId, is_primary: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supportTicket', ticketId] })
      onClose()
    },
  })

  const { containerRef: assignRef, handleKeyDown: assignKeyDown } = useFocusTrap(onClose)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div ref={assignRef} role="dialog" aria-modal="true" aria-label="Assign Agent" className="w-full max-w-sm rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()} onKeyDown={assignKeyDown}>
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="text-sm font-semibold text-gray-900">Assign Agent</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close assign agent dialog">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4">
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
          <div className="max-h-48 overflow-y-auto space-y-1">
            {agents.map((u) => (
              <button
                key={u.id}
                onClick={() => assignMutation.mutate(u.id)}
                disabled={assignMutation.isPending}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-gray-50"
              >
                <div className="h-7 w-7 rounded-full bg-gray-200 text-center text-xs leading-7 text-gray-600">
                  {(u.full_name || u.email).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{u.full_name}</p>
                  <p className="text-xs text-gray-500">{u.role}</p>
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

  const { containerRef: handoffRef, handleKeyDown: handoffKeyDown } = useFocusTrap(onClose)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div ref={handoffRef} role="dialog" aria-modal="true" aria-label="Handoff Ticket" className="w-full max-w-sm rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()} onKeyDown={handoffKeyDown}>
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="text-sm font-semibold text-gray-900">Handoff Ticket</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close handoff dialog">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <input
            type="text"
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
          <div className="max-h-36 overflow-y-auto space-y-1">
            {agents.map((u) => (
              <button
                key={u.id}
                onClick={() => setSelectedAgentId(u.id)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  selectedAgentId === u.id
                    ? 'bg-orange-50 ring-1 ring-orange-300'
                    : 'hover:bg-gray-50'
                }`}
              >
                <div className="h-7 w-7 rounded-full bg-gray-200 text-center text-xs leading-7 text-gray-600">
                  {(u.full_name || u.email).charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{u.full_name}</p>
                  <p className="text-xs text-gray-500">{u.role}</p>
                </div>
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Handoff note (optional)..."
            rows={2}
            className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
          <button
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
