/**
 * CustomerSupportPage — customer portal support tickets (X1-088 to X1-092)
 */

import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDistanceToNow } from 'date-fns'
import { Plus, ArrowLeft, Send, X } from 'lucide-react'
import { extractApiErrorMessage, useToast } from '@/lib/toast'
import type {
  SupportTicket,
  SupportTicketDetail,
  SupportTicketMessage,
  SupportTicketPriority,
} from '@/types/chat'

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-700',
}

const PRIORITY_COLORS: Record<string, string> = {
  low: 'text-gray-500',
  normal: 'text-blue-600',
  high: 'text-orange-600',
  urgent: 'text-red-600',
}

export default function CustomerSupportPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTicketId, setActiveTicketId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  // Y2-020: Auto-open create modal when navigated with ?new=1
  const prefillSubject = searchParams.get('subject') || ''
  const prefillContent = searchParams.get('content') || ''
  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setShowCreate(true)
      setSearchParams({}, { replace: true })
    }
  }, [])

  // List tickets
  const ticketsQuery = useQuery({
    queryKey: ['myTickets'],
    queryFn: () => api.getMyTickets(),
  })

  // Active ticket detail
  const ticketQuery = useQuery({
    queryKey: ['myTicket', activeTicketId],
    queryFn: () => (activeTicketId ? api.getMyTicket(activeTicketId) : Promise.reject()),
    enabled: !!activeTicketId,
  })

  const tickets = ticketsQuery.data?.items ?? []

  if (activeTicketId && ticketQuery.data) {
    return (
      <CustomerTicketView
        ticket={ticketQuery.data}
        onBack={() => setActiveTicketId(null)}
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Support</h1>
          <p className="text-sm text-gray-500">Get help from our team</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" /> New Ticket
        </button>
      </div>

      {tickets.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-12 text-center">
          <p className="text-gray-500">No support tickets yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 text-sm font-medium text-blue-600 hover:underline"
          >
            Create your first ticket
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {tickets.map((ticket: SupportTicket) => (
            <button
              key={ticket.id}
              onClick={() => setActiveTicketId(ticket.id)}
              className="w-full rounded-xl border border-gray-200 bg-white p-4 text-left transition-colors hover:bg-gray-50"
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900">{ticket.subject}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    #{ticket.id} · {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium ${PRIORITY_COLORS[ticket.priority]}`}>
                    {ticket.priority}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[ticket.status]}`}>
                    {ticket.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateTicketModal
          initialSubject={prefillSubject}
          initialContent={prefillContent}
          onClose={() => setShowCreate(false)}
          onCreate={() => {
            setShowCreate(false)
            queryClient.invalidateQueries({ queryKey: ['myTickets'] })
          }}
        />
      )}
    </div>
  )
}

/* ---- Ticket Detail View ---- */

function CustomerTicketView({
  ticket,
  onBack,
}: {
  ticket: SupportTicketDetail
  onBack: () => void
}) {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [message, setMessage] = useState('')
  const toast = useToast()
  const optimisticIdCounter = useRef(0)

  const sendMutation = useMutation({
    mutationFn: (content: string) => api.sendMyTicketMessage(ticket.id, { content }),
    onMutate: async (content: string) => {
      // Cancel outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ['myTicket', ticket.id] })
      const previous = queryClient.getQueryData<SupportTicketDetail>(['myTicket', ticket.id])

      if (currentUser && previous) {
        optimisticIdCounter.current -= 1
        const optimistic: SupportTicketMessage = {
          id: optimisticIdCounter.current,
          ticket_id: ticket.id,
          sender_id: currentUser.id,
          sender_type: 'customer',
          content,
          is_internal_note: false,
          created_at: new Date().toISOString(),
          sender_full_name: currentUser.full_name,
        }
        queryClient.setQueryData<SupportTicketDetail>(['myTicket', ticket.id], {
          ...previous,
          messages: [...previous.messages, optimistic],
        })
      }

      setMessage('')
      return { previous }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myTicket', ticket.id] })
    },
    onError: (error: unknown, _content, context) => {
      // Roll back to the previous state
      if (context?.previous) {
        queryClient.setQueryData(['myTicket', ticket.id], context.previous)
      }
      toast.error('Failed to send reply', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const closeMutation = useMutation({
    mutationFn: () => api.closeMyTicket(ticket.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myTicket', ticket.id] })
      queryClient.invalidateQueries({ queryKey: ['myTickets'] })
      toast.success('Ticket closed')
    },
    onError: (error: unknown) => {
      toast.error('Failed to close ticket', extractApiErrorMessage(error, 'Please try again.'))
    },
  })

  const canClose = ticket.status === 'open' || ticket.status === 'resolved'

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-gray-900">{ticket.subject}</h2>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>#{ticket.id}</span>
            <span className={`rounded-full px-2 py-0.5 font-medium ${STATUS_COLORS[ticket.status]}`}>
              {ticket.status.replace('_', ' ')}
            </span>
          </div>
        </div>
        {canClose && (
          <button
            onClick={() => closeMutation.mutate()}
            disabled={closeMutation.isPending}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Close Ticket
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="max-h-[60vh] overflow-y-auto p-4 space-y-4">
          {ticket.messages.filter((m) => !m.is_internal_note).length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Send className="mb-2 h-8 w-8" />
              <p className="text-sm font-medium text-gray-500">No messages yet</p>
              <p className="mt-0.5 text-xs">Send a message to start the conversation</p>
            </div>
          ) : (
          ticket.messages
            .filter((m) => !m.is_internal_note)
            .map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.sender_type === 'customer' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                    msg.sender_type === 'customer'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {msg.sender_type === 'agent' && (
                    <p className="mb-0.5 text-xs font-medium text-gray-500">
                      {msg.sender_full_name || 'Support Agent'}
                    </p>
                  )}
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                  <p className={`mt-1 text-[10px] ${
                    msg.sender_type === 'customer' ? 'text-blue-200' : 'text-gray-400'
                  }`}>
                    {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Reply input */}
        {ticket.status !== 'closed' && (
          <div className="flex items-end gap-2 border-t border-gray-200 p-3">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (message.trim()) sendMutation.mutate(message.trim())
                }
              }}
              placeholder="Type your reply..."
              rows={1}
              className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <button
              onClick={() => message.trim() && sendMutation.mutate(message.trim())}
              disabled={sendMutation.isPending || !message.trim()}
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

/* ---- Create Ticket Modal ---- */

function CreateTicketModal({
  initialSubject = '',
  initialContent = '',
  onClose,
  onCreate,
}: {
  initialSubject?: string
  initialContent?: string
  onClose: () => void
  onCreate: () => void
}) {
  const [subject, setSubject] = useState(initialSubject)
  const [content, setContent] = useState(initialContent)
  const [priority, setPriority] = useState<SupportTicketPriority>('normal')

  const createMutation = useMutation({
    mutationFn: () => api.createMyTicket({ subject, content, priority }),
    onSuccess: onCreate,
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">New Support Ticket</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4 p-6">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="Brief description of your issue"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as SupportTicketPriority)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="Describe your issue in detail..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button onClick={onClose} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
            Cancel
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || !subject.trim() || !content.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </div>
    </div>
  )
}
